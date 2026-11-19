"""Vacations: balance (HU-4.3), the employee's requests (HU-4.1) and HR's
decisions on them (HU-4.2)."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession, EmployeeReader, HrStaff
from app.api.employees import get_employee_or_404, lock_employee_or_404
from app.api.me import own_employee
from app.core.clock import today
from app.models.audit_log import AuditAction
from app.models.employee import Employee, EmployeeStatus
from app.models.user import User
from app.models.vacation import VacationRequest, VacationStatus
from app.schemas.vacation import (
    CalendarAbsence,
    PendingCount,
    UnseenDecisions,
    VacationBalanceResponse,
    VacationInboxItem,
    VacationReject,
    VacationRequestCreate,
    VacationRequestResponse,
)
from app.services.audit import record_audit
from app.services.holidays import holidays_between
from app.services.vacations import (
    CANCELLED_BY_EMPLOYEE,
    available_days_for,
    business_days,
    can_be_cancelled,
    current_contract,
    overlaps_existing,
    vacation_balance,
)

router = APIRouter(tags=["vacations"])

INBOX_LIMIT = 200  # a bound on the inbox; far above what this company will have pending


def rejected(code: int, field: str, message: str) -> HTTPException:
    # Same {"field", "message"} shape as the employee endpoints, so the form can
    # show the message under the right input.
    return HTTPException(status_code=code, detail={"field": field, "message": message})


@router.get("/me/vacation-balance", response_model=VacationBalanceResponse)
def get_my_vacation_balance(current_user: CurrentUser, db: DbSession) -> VacationBalanceResponse:
    """HU-4.3 CA03: the signed-in person's own balance. No id in the path: the
    record comes from the session, so nobody can ask for someone else's."""
    return VacationBalanceResponse.of(vacation_balance(db, own_employee(current_user, db)))


@router.get("/employees/{employee_id}/vacation-balance", response_model=VacationBalanceResponse)
def get_vacation_balance(
    employee_id: uuid.UUID,
    db: DbSession,
    current_user: EmployeeReader,  # session required (401) and role check (403)
) -> VacationBalanceResponse:
    """HU-4.3: any employee's balance, for those who read records."""
    return VacationBalanceResponse.of(vacation_balance(db, get_employee_or_404(db, employee_id)))


@router.post(
    "/me/vacation-requests",
    response_model=VacationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_my_vacation_request(
    data: VacationRequestCreate,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> VacationRequest:
    """HU-4.1: an employee asks for a range of days off. It stays PENDIENTE (CA04).

    Every rule is checked here, never only in the browser. The employee's row is
    locked first (FOR UPDATE): two requests sent at the same time are checked one
    after the other, so together they cannot exceed the balance.
    """
    employee = lock_employee_or_404(db, own_employee(current_user, db).id)
    contract = current_contract(db, employee.id)
    if employee.status is not EmployeeStatus.ACTIVO or contract is None:
        raise rejected(409, "status", "Only an active employee with a contract can request vacations")

    if data.start_date < today():
        raise rejected(422, "start_date", "Vacations cannot start in the past")
    if contract.end_date is not None and data.end_date > contract.end_date:
        raise rejected(422, "end_date", "Vacations cannot end after the contract")

    # CA02: weekends are left out, and holidays too (HU-4.6).
    holidays = holidays_between(db, data.start_date, data.end_date)
    days = business_days(data.start_date, data.end_date, holidays)
    if days == 0:
        raise rejected(422, "end_date", "The range has no business days (only weekends or holidays)")

    if overlaps_existing(db, employee.id, data.start_date, data.end_date):
        raise rejected(409, "start_date", "The range overlaps another pending or approved request")

    # CA03, decision 3: pending requests also hold days, or two requests could
    # each fit the balance and exceed it together once both are approved.
    balance = vacation_balance(db, employee)
    if days > balance.requestable:
        raise rejected(409, "business_days", f"Only {balance.requestable} days can be requested")

    vacation = VacationRequest(
        id=uuid.uuid4(),  # known before the flush, for the audit row
        employee_id=employee.id,
        start_date=data.start_date,
        end_date=data.end_date,
        business_days=days,
        status=VacationStatus.PENDIENTE,
        requested_by_id=current_user.id,
    )
    db.add(vacation)
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.VACATION_REQUESTED,
        entity_type="vacation_request",
        entity_id=vacation.id,
        changes={
            "start_date": (None, data.start_date),
            "end_date": (None, data.end_date),
            "business_days": (None, days),
            "status": (None, VacationStatus.PENDIENTE),
        },
    )
    db.commit()
    db.refresh(vacation)
    return vacation


def _inbox_item(
    vacation: VacationRequest, employee: Employee, available: Decimal
) -> VacationInboxItem:
    return VacationInboxItem(
        **VacationRequestResponse.model_validate(vacation).model_dump(),
        employee_id=employee.id,
        employee_name=f"{employee.first_names} {employee.last_names}",
        available_days=available,
    )


@router.get("/vacation-requests", response_model=list[VacationInboxItem])
def list_vacation_requests(
    db: DbSession,
    current_user: HrStaff,  # session required (401) and ADMIN or HR role (403)
    status_filter: Annotated[VacationStatus, Query(alias="status")] = VacationStatus.PENDIENTE,
) -> list[VacationInboxItem]:
    """HU-4.2 CA01: HR's inbox. PENDIENTE by default, the nearest dates first."""
    rows = db.execute(
        select(VacationRequest, Employee)
        .join(Employee, Employee.id == VacationRequest.employee_id)
        .where(VacationRequest.status == status_filter)
        .order_by(VacationRequest.start_date, VacationRequest.created_at)
        .limit(INBOX_LIMIT)
    ).all()
    # One batch for every row: the per-row balance was an N+1 (3 queries per row).
    available = available_days_for(db, list({employee.id: employee for _, employee in rows}.values()))
    return [_inbox_item(vacation, employee, available[employee.id]) for vacation, employee in rows]


@router.get("/vacation-requests/pending-count", response_model=PendingCount)
def count_pending_requests(db: DbSession, current_user: HrStaff) -> PendingCount:
    """HU-4.7 CA01: the number next to "Solicitudes de vacaciones" in the sidebar.
    A COUNT in the database: the badge never loads the requests themselves."""
    total = db.scalar(
        select(func.count())
        .select_from(VacationRequest)
        .where(VacationRequest.status == VacationStatus.PENDIENTE)
    )
    return PendingCount(count=total or 0)


def _lock_pending_request(
    db: Session, request_id: uuid.UUID, current_user: User
) -> tuple[VacationRequest, Employee]:
    """Lock the employee, then the request, in the same order as every other
    write (a request, a departure): one order everywhere means no deadlock."""
    found = db.get(VacationRequest, request_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Vacation request not found")
    employee = lock_employee_or_404(db, found.employee_id)
    vacation = db.scalars(
        select(VacationRequest)
        .where(VacationRequest.id == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)  # read the status again after the lock
    ).one()
    if vacation.status is not VacationStatus.PENDIENTE:
        raise rejected(409, "status", "Only a pending request can be decided")
    # Nobody approves their own vacations, not even an ADMIN.
    if current_user.employee_id == employee.id:
        raise rejected(403, "employee", "You cannot decide on your own request")
    return vacation, employee


@router.post("/vacation-requests/{request_id}/approve", response_model=VacationInboxItem)
def approve_vacation_request(
    request_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: HrStaff,
) -> VacationInboxItem:
    """HU-4.2 CA02: APROBADA; its days now count as used in the balance.

    Nothing is subtracted by hand: the balance is calculated from the approved
    requests, so changing the status IS the discount. It is checked once more
    here, because the balance may have changed since the employee asked.
    """
    vacation, employee = _lock_pending_request(db, request_id, current_user)
    if employee.status is not EmployeeStatus.ACTIVO:
        raise rejected(409, "status", "The employee is no longer active")
    available = vacation_balance(db, employee).available
    if vacation.business_days > available:
        raise rejected(409, "business_days", f"Only {available} days are available")

    vacation.status = VacationStatus.APROBADA
    vacation.decided_by_id = current_user.id
    vacation.decided_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.VACATION_APPROVED,
        entity_type="vacation_request",
        entity_id=vacation.id,
        changes={"status": (VacationStatus.PENDIENTE, VacationStatus.APROBADA)},
    )
    db.commit()
    return _inbox_item(vacation, employee, vacation_balance(db, employee).available)


@router.post("/vacation-requests/{request_id}/reject", response_model=VacationInboxItem)
def reject_vacation_request(
    request_id: uuid.UUID,
    data: VacationReject,
    request: Request,
    db: DbSession,
    current_user: HrStaff,
) -> VacationInboxItem:
    """HU-4.2 CA03: RECHAZADA with a mandatory reason; no days are used."""
    vacation, employee = _lock_pending_request(db, request_id, current_user)
    vacation.status = VacationStatus.RECHAZADA
    vacation.reason = data.reason
    vacation.decided_by_id = current_user.id
    vacation.decided_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.VACATION_REJECTED,
        entity_type="vacation_request",
        entity_id=vacation.id,
        changes={
            "status": (VacationStatus.PENDIENTE, VacationStatus.RECHAZADA),
            "reason": (None, data.reason),
        },
    )
    db.commit()
    return _inbox_item(vacation, employee, vacation_balance(db, employee).available)


def _month_bounds(month: str) -> tuple[date, date]:
    """'2026-11' -> (2026-11-01, 2026-11-30). The pattern already checked the shape."""
    year, number = int(month[:4]), int(month[5:])
    first = date(year, number, 1)
    following = date(year + number // 12, number % 12 + 1, 1)
    return first, following - timedelta(days=1)


@router.get("/vacation-calendar", response_model=list[CalendarAbsence])
def get_vacation_calendar(
    db: DbSession,
    current_user: EmployeeReader,  # ADMIN, HR and MANAGER plan around absences
    month: Annotated[str, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")],
    area: Annotated[str | None, Query(max_length=120)] = None,
) -> list[CalendarAbsence]:
    """HU-4.4: APPROVED vacations that touch the month (CA02), including those
    that start before it or end after it; the calendar draws only its own days.

    HU-4.8: `area` keeps only that area's people, filtered by the database (an
    exact match: the value comes from GET /employees/areas)."""
    first, last = _month_bounds(month)
    query = (
        select(VacationRequest, Employee)
        .join(Employee, Employee.id == VacationRequest.employee_id)
        .where(
            VacationRequest.status == VacationStatus.APROBADA,
            VacationRequest.start_date <= last,
            VacationRequest.end_date >= first,
        )
        .order_by(VacationRequest.start_date, Employee.last_names, Employee.first_names)
    )
    if area is not None and area.strip() != "":
        query = query.where(Employee.area == area.strip())
    rows = db.execute(query).all()
    return [
        CalendarAbsence(
            request_id=vacation.id,
            employee_id=employee.id,
            employee_name=f"{employee.first_names} {employee.last_names}",
            area=employee.area,
            start_date=vacation.start_date,
            end_date=vacation.end_date,
        )
        for vacation, employee in rows
    ]


@router.get("/me/vacation-requests", response_model=list[VacationRequestResponse])
def list_my_vacation_requests(current_user: CurrentUser, db: DbSession) -> list[VacationRequest]:
    """HU-4.1: my requests and their status, the latest dates first."""
    employee = own_employee(current_user, db)
    return list(
        db.scalars(
            select(VacationRequest)
            .where(VacationRequest.employee_id == employee.id)
            .order_by(VacationRequest.start_date.desc(), VacationRequest.created_at.desc())
        )
    )


@router.post("/me/vacation-requests/{request_id}/cancel", response_model=VacationRequestResponse)
def cancel_my_vacation_request(
    request_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser,
    db: DbSession,
) -> VacationRequest:
    """HU-4.5: the employee withdraws a request that is PENDING, or APPROVED and
    not started yet (CA01). Nothing is given back by hand: the balance is
    calculated from the requests, so CANCELADA frees the days at once (CA02).

    Someone else's request answers 404, the same as one that does not exist:
    a 403 would confirm that the id is real.
    """
    owner = own_employee(current_user, db)
    found = db.get(VacationRequest, request_id)
    if found is None or found.employee_id != owner.id:
        raise HTTPException(status_code=404, detail="Vacation request not found")

    # The same lock order as every other write: employee first, then the request.
    lock_employee_or_404(db, owner.id)
    vacation = db.scalars(
        select(VacationRequest)
        .where(VacationRequest.id == request_id)
        .with_for_update()
        .execution_options(populate_existing=True)  # HR may have decided it meanwhile
    ).one()
    if not can_be_cancelled(vacation, today()):
        raise rejected(409, "status", "Only a pending request, or an approved one not started yet, can be cancelled")

    previous = vacation.status
    vacation.status = VacationStatus.CANCELADA
    vacation.reason = CANCELLED_BY_EMPLOYEE
    vacation.decided_by_id = current_user.id
    vacation.decided_at = datetime.now(timezone.utc)
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.VACATION_CANCELLED,
        entity_type="vacation_request",
        entity_id=vacation.id,
        changes={"status": (previous, VacationStatus.CANCELADA)},
    )
    db.commit()
    db.refresh(vacation)
    return vacation


@router.get("/me/vacation-requests/unseen", response_model=UnseenDecisions)
def my_unseen_decisions(current_user: CurrentUser, db: DbSession) -> UnseenDecisions:
    """HU-4.7 CA02: my requests decided since my last visit to "Mis vacaciones".

    Only decisions made by someone else are news: what I cancelled myself I
    already know. Never visited means every past decision counts once."""
    employee = own_employee(current_user, db)
    query = select(VacationRequest.id).where(
        VacationRequest.employee_id == employee.id,
        VacationRequest.decided_at.is_not(None),
        or_(
            VacationRequest.decided_by_id.is_(None),
            VacationRequest.decided_by_id != current_user.id,
        ),
    )
    if current_user.vacations_seen_at is not None:
        query = query.where(VacationRequest.decided_at > current_user.vacations_seen_at)
    ids = list(db.scalars(query.order_by(VacationRequest.decided_at.desc())))
    return UnseenDecisions(count=len(ids), request_ids=ids)


@router.post("/me/vacation-requests/seen", status_code=status.HTTP_204_NO_CONTENT)
def mark_my_decisions_seen(current_user: CurrentUser, db: DbSession) -> Response:
    """HU-4.7 CA02: "Mis vacaciones" was opened; what was decided so far is no
    longer news. Not audited: it changes nothing about the requests."""
    own_employee(current_user, db)  # 404 for an account without a record, like the rest
    current_user.vacations_seen_at = datetime.now(timezone.utc)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
