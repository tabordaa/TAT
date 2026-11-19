"""Vacation balance (HU-4.3) and business days (HU-4.1).

The balance is CALCULATED every time it is read, never stored in a column:

- What is earned grows with today's date, so a stored counter would need a
  scheduled job to stay right.
- Approving, rejecting or cancelling a request changes the result at once,
  because the result is derived from the requests themselves.
- A rehire starts from zero, because only the contract in force counts.

With no counter there is nothing that can drift out of sync. Concurrency is
handled where requests are written: the employee's row is locked (FOR UPDATE)
while a request is created or approved.
"""

import uuid
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import ROUND_DOWN, Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models.employee import Employee, EmployeeStatus, EmploymentContract
from app.models.vacation import VacationRequest, VacationStatus

DAYS_PER_YEAR = 15  # Colombian labor law: 15 business days per year worked
_CENTS = Decimal("0.01")
_DAYS_IN_YEAR = Decimal(365)


@dataclass(frozen=True)
class VacationBalance:
    contract_start: date | None
    accrued: Decimal  # earned in the contract in force (decision 4: proportional)
    used: int  # APPROVED requests (CA02)
    pending: int  # requests still waiting for a decision
    available: Decimal  # accrued - used
    requestable: Decimal  # available - pending (decision 3)


def business_days(start: date, end: date, holidays: AbstractSet[date] = frozenset()) -> int:
    """Monday to Friday between both dates, inclusive, minus the `holidays` that
    fall on one of those days (HU-4.6; until then decision 6 counted them).

    The function stays pure: the caller loads the holidays (holidays_between),
    so it can be tested without a database."""
    if end < start:
        return 0
    full_weeks, extra = divmod((end - start).days + 1, 7)
    count = full_weeks * 5
    for offset in range(extra):
        if (start + timedelta(days=full_weeks * 7 + offset)).weekday() < 5:
            count += 1
    # A holiday on a Saturday or a Sunday was never counted in the first place.
    return count - sum(1 for day in holidays if start <= day <= end and day.weekday() < 5)


def accrued_days(contract_start: date, on: date) -> Decimal:
    """15 days per 365 days of service, rounded DOWN to cents: a fraction of a
    day is not promised until it is fully earned."""
    days_worked = max((on - contract_start).days, 0)
    return (DAYS_PER_YEAR * Decimal(days_worked) / _DAYS_IN_YEAR).quantize(
        _CENTS, rounding=ROUND_DOWN
    )


def current_contract(db: Session, employee_id: uuid.UUID) -> EmploymentContract | None:
    """The contract in force (terminated_on is NULL), if any."""
    return db.scalars(
        select(EmploymentContract)
        .where(
            EmploymentContract.employee_id == employee_id,
            EmploymentContract.terminated_on.is_(None),
        )
        .order_by(EmploymentContract.start_date.desc())
        .limit(1)
    ).first()


def _days_in(db: Session, employee_id: uuid.UUID, since: date, status: VacationStatus) -> int:
    total = db.scalar(
        select(func.coalesce(func.sum(VacationRequest.business_days), 0)).where(
            VacationRequest.employee_id == employee_id,
            VacationRequest.status == status,
            # Decision 5: requests of a previous contract do not count.
            VacationRequest.start_date >= since,
        )
    )
    return int(total or 0)


def overlaps_existing(
    db: Session, employee_id: uuid.UUID, start: date, end: date, exclude: uuid.UUID | None = None
) -> bool:
    """Decision 7: a range may not touch a PENDING or APPROVED request of the same
    employee. Two ranges overlap when each one starts before the other ends."""
    query = select(VacationRequest.id).where(
        VacationRequest.employee_id == employee_id,
        VacationRequest.status.in_((VacationStatus.PENDIENTE, VacationStatus.APROBADA)),
        VacationRequest.start_date <= end,
        VacationRequest.end_date >= start,
    )
    if exclude is not None:
        query = query.where(VacationRequest.id != exclude)
    return db.scalar(query.limit(1)) is not None


CANCELLED_ON_DEPARTURE = "Contrato finalizado"
CANCELLED_BY_EMPLOYEE = "Cancelada por el empleado"


def can_be_cancelled(vacation: VacationRequest, on: date) -> bool:
    """HU-4.5 CA01: a PENDING request, or an APPROVED one that has not started.
    Once the first day has come, the days are being taken: HR must handle it."""
    if vacation.status is VacationStatus.PENDIENTE:
        return True
    return vacation.status is VacationStatus.APROBADA and vacation.start_date > on


def cancel_pending_requests(
    db: Session, employee_id: uuid.UUID, actor_id: uuid.UUID, when: datetime
) -> int:
    """Decision 8: when an employee leaves, nobody should approve their pending
    requests later. They become CANCELADA in the departure's own transaction.
    Approved ones are kept: they are history, and they stop counting anyway
    because the balance only looks at the contract in force."""
    pending = db.scalars(
        select(VacationRequest)
        .where(
            VacationRequest.employee_id == employee_id,
            VacationRequest.status == VacationStatus.PENDIENTE,
        )
        .with_for_update()
    ).all()
    for vacation in pending:
        vacation.status = VacationStatus.CANCELADA
        vacation.reason = CANCELLED_ON_DEPARTURE
        vacation.decided_by_id = actor_id
        vacation.decided_at = when
    return len(pending)


def vacation_balance(db: Session, employee: Employee) -> VacationBalance:
    """The balance as of the business date (Colombia), from the contract in force."""
    contract = current_contract(db, employee.id) if employee.status is EmployeeStatus.ACTIVO else None
    if contract is None:
        zero = Decimal("0.00")
        return VacationBalance(None, zero, 0, 0, zero, zero)

    accrued = accrued_days(contract.start_date, today())
    used = _days_in(db, employee.id, contract.start_date, VacationStatus.APROBADA)
    pending = _days_in(db, employee.id, contract.start_date, VacationStatus.PENDIENTE)
    available = accrued - used
    return VacationBalance(
        contract_start=contract.start_date,
        accrued=accrued,
        used=used,
        pending=pending,
        available=available,
        requestable=available - pending,
    )


def available_days_for(db: Session, employees: list[Employee]) -> dict[uuid.UUID, Decimal]:
    """`vacation_balance(...).available` for many employees in a fixed number of
    queries. The inbox used to call vacation_balance() once per row: three round
    trips each, which against a remote database meant seconds for a few dozen rows.

    Same rules as vacation_balance(): only ACTIVE employees with a contract in
    force earn days, and only APPROVED requests of that contract are subtracted.
    """
    zero = Decimal("0.00")
    result = {employee.id: zero for employee in employees}
    active_ids = [e.id for e in employees if e.status is EmployeeStatus.ACTIVO]
    if not active_ids:
        return result

    on = today()

    q_contracts = (
        select(EmploymentContract.employee_id, EmploymentContract.start_date)
        .where(
            EmploymentContract.employee_id.in_(active_ids),
            EmploymentContract.terminated_on.is_(None)
        )
    )

    contract_starts: dict[uuid.UUID, date] = dict(db.execute(q_contracts).tuples().all())

    if not contract_starts:
        return result

    q_used = (
        select(
            VacationRequest.employee_id,
            func.sum(VacationRequest.business_days)
        )
        .select_from(VacationRequest)
        .join(EmploymentContract, VacationRequest.employee_id == EmploymentContract.employee_id)
        .where(
            VacationRequest.employee_id.in_(contract_starts.keys()),
            EmploymentContract.terminated_on.is_(None),
            VacationRequest.start_date >= EmploymentContract.start_date,
            VacationRequest.status == VacationStatus.APROBADA
        )
        .group_by(VacationRequest.employee_id)
    )
    used: dict[uuid.UUID, int] = dict(db.execute(q_used).tuples().all())

    for employee_id, start in contract_starts.items():
        result[employee_id] = accrued_days(start, on) - used.get(employee_id, 0)
    return result
