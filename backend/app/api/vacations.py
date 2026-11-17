"""Vacations: balance (HU-4.3) and the employee's own requests (HU-4.1)."""

import uuid

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, EmployeeReader
from app.api.employees import get_employee_or_404, lock_employee_or_404
from app.api.me import own_employee
from app.core.clock import today
from app.models.audit_log import AuditAction
from app.models.employee import EmployeeStatus
from app.models.vacation import VacationRequest, VacationStatus
from app.schemas.vacation import (
    VacationBalanceResponse,
    VacationRequestCreate,
    VacationRequestResponse,
)
from app.services.audit import record_audit
from app.services.vacations import (
    business_days,
    current_contract,
    overlaps_existing,
    vacation_balance,
)

router = APIRouter(tags=["vacations"])


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

    days = business_days(data.start_date, data.end_date)  # CA02: weekends are left out
    if days == 0:
        raise rejected(422, "end_date", "The range has no business days")

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
