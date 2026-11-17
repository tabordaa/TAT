"""HU-3.1 Contract assignment and rehire, HU-3.3 Contract termination."""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import cast

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import DbSession, EmployeeReader, HrStaff
from app.api.employees import (
    DUPLICATE_DOCUMENT,
    DUPLICATE_EMAIL,
    UNIQUE_VIOLATIONS,
    conflict,
    get_employee_or_404,
    lock_employee_or_404,
)
from app.core.clock import today
from app.models.audit_log import AuditAction
from app.models.employee import Employee, EmployeeStatus, EmploymentContract
from app.models.user import User, UserRole
from app.schemas.employee import (
    ContractAlert,
    ContractAssign,
    ContractResponse,
    ContractTerminate,
    EmployeeResponse,
)
from app.services.audit import record_audit
from app.services.vacations import cancel_pending_requests

router = APIRouter(prefix="/employees", tags=["contracts"])

ALERT_WINDOW_DAYS = 30
ALERT_LIMIT = 100


def _other_active_admins(db: Session, account_id: uuid.UUID) -> int:
    """Active ADMIN accounts besides this one, with their rows locked.

    The lock makes two simultaneous terminations queue up: if two admins end
    each other's contract at once, the second one waits, then sees the first
    admin already inactive and is refused. Without it both would count "one
    more admin left" and the system could end up with none.
    """
    locked = db.scalars(
        select(User.id)
        .where(User.role == UserRole.ADMIN, User.is_active.is_(True), User.id != account_id)
        .with_for_update()
    ).all()
    return len(locked)


def _ensure_admin_can_leave(db: Session, account: User, actor: User) -> None:
    """S12 (Kevin, 3 nov): HR never ends an ADMIN's contract, and the last
    active ADMIN cannot be terminated (nobody could administer the system)."""
    if account.role is not UserRole.ADMIN:
        return
    if actor.role is not UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "field": "account_role",
                "message": "Only an administrator can terminate an administrator",
            },
        )
    if account.is_active and _other_active_admins(db, account.id) == 0:
        raise conflict("last_admin", "The last active administrator cannot be terminated")


def _reject_duplicates_of_a_rehire(db: Session, employee: Employee) -> None:
    """While inactive, someone else may have taken this document or email."""
    active_other = (
        Employee.status == EmployeeStatus.ACTIVO,
        Employee.id != employee.id,
    )
    if db.scalar(
        select(Employee.id).where(
            *active_other,
            Employee.document_type == employee.document_type,
            Employee.document_number == employee.document_number,
        )
    ):
        raise conflict("document_number", DUPLICATE_DOCUMENT)
    if db.scalar(select(Employee.id).where(*active_other, Employee.email == employee.email)):
        raise conflict("email", DUPLICATE_EMAIL)


def _close_open_contracts(db: Session, employee_id: uuid.UUID, on: date) -> None:
    db.execute(
        update(EmploymentContract)
        .where(
            EmploymentContract.employee_id == employee_id,
            EmploymentContract.terminated_on.is_(None),
        )
        .values(terminated_on=on)
    )


@router.get("/contract-alerts", response_model=list[ContractAlert])
def list_contract_alerts(
    db: DbSession,
    current_user: EmployeeReader,  # session required (401) and role check (403)
) -> list[ContractAlert]:
    """HU-3.2: active employees whose contract ends in under 30 days.

    A contract already past its date stays listed: an active employee without a
    valid contract is the case that most needs someone's attention.
    """
    now = today()
    rows = db.scalars(
        select(Employee)
        .where(
            Employee.status == EmployeeStatus.ACTIVO,
            Employee.end_date.is_not(None),
            Employee.end_date < now + timedelta(days=ALERT_WINDOW_DAYS),
        )
        .order_by(Employee.end_date, Employee.last_names, Employee.id)
        .limit(ALERT_LIMIT)
    ).all()
    alerts = []
    for employee in rows:
        end_date = cast(date, employee.end_date)  # filtered above: never None here
        days_left = (end_date - now).days
        alerts.append(
            ContractAlert(
                id=employee.id,
                first_names=employee.first_names,
                last_names=employee.last_names,
                position=employee.position,
                end_date=end_date,
                days_left=days_left,
                state="VENCIDO" if days_left < 0 else "POR_VENCER",
            )
        )
    return alerts


@router.get("/{employee_id}/contracts", response_model=list[ContractResponse])
def list_contracts(
    employee_id: uuid.UUID,
    db: DbSession,
    current_user: EmployeeReader,  # session required (401) and role check (403)
) -> list[EmploymentContract]:
    get_employee_or_404(db, employee_id)
    return list(
        db.scalars(
            select(EmploymentContract)
            .where(EmploymentContract.employee_id == employee_id)
            # Open contract first, then the most recent; id keeps the order stable.
            .order_by(
                EmploymentContract.terminated_on.is_(None).desc(),
                EmploymentContract.start_date.desc(),
                EmploymentContract.id,
            )
        )
    )


@router.post(
    "/{employee_id}/contracts",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_contract(
    employee_id: uuid.UUID,
    data: ContractAssign,
    request: Request,
    db: DbSession,
    current_user: HrStaff,  # session required (401) and ADMIN or HR role (403)
) -> Employee:
    """HU-3.1: a new contract; if the employee was INACTIVO, this is the rehire.

    The rehire does NOT reopen the login account: giving access back is a
    separate decision for an administrator (the password reset of HU-1.5).
    """
    employee = lock_employee_or_404(db, employee_id)
    is_rehire = employee.status is EmployeeStatus.INACTIVO
    if is_rehire:
        _reject_duplicates_of_a_rehire(db, employee)

    # History must read forward: nothing may start before what already happened.
    last_start, last_end = db.execute(
        select(
            func.max(EmploymentContract.start_date),
            func.max(EmploymentContract.terminated_on),
        ).where(EmploymentContract.employee_id == employee.id)
    ).one()
    latest = max(filter(None, (last_start, last_end)), default=None)
    if latest is not None and data.start_date < latest:
        raise conflict(
            "start_date", "The new contract cannot start before the previous one"
        )

    changes: dict[str, tuple[object, object]] = {
        "contract_type": (employee.contract_type, data.contract_type),
        "start_date": (employee.start_date, data.start_date),
        "end_date": (employee.end_date, data.end_date),
    }
    if is_rehire:
        changes["status"] = (employee.status, EmployeeStatus.ACTIVO)

    _close_open_contracts(db, employee.id, data.start_date)
    db.add(
        EmploymentContract(
            employee_id=employee.id,
            contract_type=data.contract_type,
            start_date=data.start_date,
            end_date=data.end_date,
            created_by_id=current_user.id,
        )
    )
    employee.contract_type = data.contract_type
    employee.start_date = data.start_date
    employee.end_date = data.end_date
    employee.status = EmployeeStatus.ACTIVO  # set by the server, never by the client
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.EMPLOYEE_REHIRED if is_rehire else AuditAction.CONTRACT_ASSIGNED,
        entity_type="employee",
        entity_id=employee.id,
        changes=changes,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        # The partial unique indexes catch what the check above could not see.
        db.rollback()
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint in UNIQUE_VIOLATIONS:
            raise conflict(*UNIQUE_VIOLATIONS[constraint]) from exc
        raise
    return employee


@router.post("/{employee_id}/contracts/terminate", response_model=EmployeeResponse)
def terminate_contract(
    employee_id: uuid.UUID,
    data: ContractTerminate,
    request: Request,
    db: DbSession,
    current_user: HrStaff,  # session required (401) and ADMIN or HR role (403)
) -> Employee:
    """HU-3.3: the employee leaves. The record stays; access ends right now."""
    employee = lock_employee_or_404(db, employee_id)
    if employee.status is EmployeeStatus.INACTIVO:
        raise conflict("status", "This employee is already inactive")

    if data.end_date < employee.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "field": "end_date",
                "message": "The end date cannot be before the contract start date",
            },
        )
    # The status changes today, so a future date would describe something false.
    if data.end_date > today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"field": "end_date", "message": "The end date cannot be in the future"},
        )

    account = db.scalar(select(User).where(User.employee_id == employee.id))
    if account is not None and account.id == current_user.id:
        raise conflict("account", "You cannot terminate your own contract")
    if account is not None:
        _ensure_admin_can_leave(db, account, current_user)

    changes: dict[str, tuple[object, object]] = {
        "status": (employee.status, EmployeeStatus.INACTIVO),
        "end_date": (employee.end_date, data.end_date),
    }
    if account is not None:
        changes["is_active"] = (account.is_active, False)
        account.is_active = False
        account.token_version += 1  # any open session ends now, not when it expires

    employee.status = EmployeeStatus.INACTIVO
    employee.end_date = data.end_date
    _close_open_contracts(db, employee.id, data.end_date)
    cancelled = cancel_pending_requests(
        db, employee.id, current_user.id, datetime.now(timezone.utc)
    )
    if cancelled:
        changes["pending_vacation_requests"] = (cancelled, 0)
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.CONTRACT_TERMINATED,
        entity_type="employee",
        entity_id=employee.id,
        changes=changes,
    )
    db.commit()
    return employee
