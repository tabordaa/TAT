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
from dataclasses import dataclass
from datetime import date, timedelta
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


def business_days(start: date, end: date) -> int:
    """Monday to Friday between both dates, inclusive. Holidays count as work
    days (decision 6: only weekends are left out, as CA02 of HU-4.1 says)."""
    if end < start:
        return 0
    full_weeks, extra = divmod((end - start).days + 1, 7)
    count = full_weeks * 5
    for offset in range(extra):
        if (start + timedelta(days=full_weeks * 7 + offset)).weekday() < 5:
            count += 1
    return count


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
