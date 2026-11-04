"""HU-2.1 registration, HU-2.2 directory (list and search), HU-2.3 detail."""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.api.deps import Admin, DbSession, EmployeeReader, HrStaff
from app.api.me import Storage, photo_response
from app.core.security import generate_temporary_password, hash_password
from app.models.audit_log import AuditAction
from app.models.employee import Employee, EmployeeStatus, EmploymentContract
from app.models.user import User, UserRole
from app.schemas.employee import (
    AccountCreated,
    CountItem,
    EmployeeCreate,
    EmployeeCreatedResponse,
    EmployeeDetailResponse,
    EmployeeListItem,
    EmployeeListResponse,
    EmployeeOverview,
    EmployeeResponse,
    EmployeeStats,
    PersonSummary,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/employees", tags=["employees"])

DUPLICATE_DOCUMENT = "An active employee with this document already exists"
DUPLICATE_EMAIL = "An active employee with this email already exists"
DUPLICATE_ACCOUNT = "An access account with this email already exists"
ACCOUNT_ADMIN_ONLY = "Only an administrator can create access accounts"

RECENT_LIMIT = 5  # rows in the dashboard's "recent hires / departures" lists
POSITIONS_SHOWN = 6  # biggest positions drawn as their own bar; the rest are grouped
OTHERS_LABEL = "Otros"

# Partial unique index name -> (field reported to the client, message).
UNIQUE_VIOLATIONS = {
    "uq_employees_active_document": ("document_number", DUPLICATE_DOCUMENT),
    "uq_employees_active_email": ("email", DUPLICATE_EMAIL),
    "ix_users_email": ("email", DUPLICATE_ACCOUNT),
}


def conflict(field: str, message: str) -> HTTPException:
    # Structured detail so the frontend can show the error under the right field.
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"field": field, "message": message},
    )


@router.post(
    "", response_model=EmployeeCreatedResponse, status_code=status.HTTP_201_CREATED
)
def create_employee(
    data: EmployeeCreate,
    request: Request,
    response: Response,
    db: DbSession,
    current_user: HrStaff,  # session required (401) and ADMIN or HR role (403)
) -> EmployeeCreatedResponse:
    # Creating a login account is more sensitive than registering a person:
    # HR may register employees, only an ADMIN may hand out credentials.
    if data.account_role is not None and current_user.role is not UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ACCOUNT_ADMIN_ONLY
        )

    document_number = data.document_number.upper()
    email = str(data.email).lower()

    # 1) Friendly, fast checks for the common case. Only ACTIVO employees
    #    count: an INACTIVO record must not block a rehire.
    active = Employee.status == EmployeeStatus.ACTIVO
    document_taken = db.scalar(
        select(Employee.id).where(
            active,
            Employee.document_type == data.document_type,
            Employee.document_number == document_number,
        )
    )
    if document_taken is not None:
        raise conflict("document_number", DUPLICATE_DOCUMENT)

    email_taken = db.scalar(select(Employee.id).where(active, Employee.email == email))
    if email_taken is not None:
        raise conflict("email", DUPLICATE_EMAIL)

    if data.account_role is not None:
        account_taken = db.scalar(select(User.id).where(User.email == email))
        if account_taken is not None:
            raise conflict("email", DUPLICATE_ACCOUNT)

    employee = Employee(
        **data.model_dump(exclude={"document_number", "email", "account_role"}),
        document_number=document_number,
        email=email,
        status=EmployeeStatus.ACTIVO,  # set by the server, never by the client
        created_by_id=current_user.id,  # audit trail
    )
    db.add(employee)

    account: AccountCreated | None = None
    # 2) The unique indexes are the real guarantee: if two requests pass the
    #    checks above at the same time, the database rejects one. Employee,
    #    account and audit rows are saved in ONE transaction: all or nothing.
    try:
        db.flush()  # assigns employee.id so the account and audit can point at it
        db.add(
            EmploymentContract(
                employee_id=employee.id,
                contract_type=employee.contract_type,
                start_date=employee.start_date,
                end_date=employee.end_date,
                created_by_id=current_user.id,
            )
        )
        record_audit(
            db,
            actor=current_user,
            request=request,
            action=AuditAction.EMPLOYEE_CREATED,
            entity_type="employee",
            entity_id=employee.id,
            changes={
                "status": (None, employee.status),
                "position": (None, employee.position),
                "area": (None, employee.area),
                "salary": (None, employee.salary),
                "contract_type": (None, employee.contract_type),
                "start_date": (None, employee.start_date),
                "end_date": (None, employee.end_date),
            },
        )
        if data.account_role is not None:
            temporary_password = generate_temporary_password()
            new_user = User(
                email=email,
                full_name=f"{employee.first_names} {employee.last_names}",
                hashed_password=hash_password(
                    temporary_password
                ),  # never the plain text
                role=data.account_role,
                must_change_password=True,
                employee_id=employee.id,
            )
            db.add(new_user)
            db.flush()  # the unique email surfaces here; assigns new_user.id
            record_audit(
                db,
                actor=current_user,
                request=request,
                action=AuditAction.ACCOUNT_CREATED,
                entity_type="user",
                entity_id=new_user.id,
                changes={
                    "email": (None, email),
                    "role": (None, data.account_role),
                },
            )
            account = AccountCreated(
                email=email,
                role=data.account_role,
                temporary_password=temporary_password,
                must_change_password=True,
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        diag = getattr(exc.orig, "diag", None)
        constraint = getattr(diag, "constraint_name", None)
        if constraint in UNIQUE_VIOLATIONS:
            raise conflict(*UNIQUE_VIOLATIONS[constraint]) from exc
        raise

    db.refresh(employee)
    if account is not None:
        # The body holds a credential: keep browsers and proxies from caching it.
        response.headers["Cache-Control"] = "no-store"
    return EmployeeCreatedResponse(
        **EmployeeResponse.model_validate(employee).model_dump(), account=account
    )


def _like_pattern(term: str) -> str:
    """Contains-match pattern for ILIKE, with the user's % and _ taken literally."""
    escaped = term.replace("\\", r"\\").replace("%", r"\%").replace("_", r"\_")
    return f"%{escaped}%"


@router.get("", response_model=EmployeeListResponse)
def list_employees(
    db: DbSession,
    current_user: EmployeeReader,  # session required (401) and role check (403)
    q: Annotated[
        str | None,
        Query(max_length=100, description="Words to find in names or document number"),
    ] = None,
    employee_status: Annotated[
        EmployeeStatus | None,
        Query(alias="status", description="Filter by ACTIVO or INACTIVO; omit for all"),
    ] = None,
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> EmployeeListResponse:
    conditions = []

    # Every word must match the first names, last names or document number
    # ("ana perez" finds Ana Maria PEREZ), case-insensitively.
    for term in (q or "").split():
        pattern = _like_pattern(term)
        conditions.append(
            or_(
                Employee.first_names.ilike(pattern, escape="\\"),
                Employee.last_names.ilike(pattern, escape="\\"),
                Employee.document_number.ilike(pattern, escape="\\"),
            )
        )
    if employee_status is not None:
        conditions.append(Employee.status == employee_status)

    total = (
        db.scalar(select(func.count()).select_from(Employee).where(*conditions)) or 0
    )

    rows = db.scalars(
        select(Employee)
        .where(*conditions)
        # Deterministic order (id breaks ties) so pages never repeat or skip rows.
        .order_by(Employee.last_names, Employee.first_names, Employee.id)
        .offset((page - 1) * size)
        .limit(size)
    ).all()

    return EmployeeListResponse(
        items=[EmployeeListItem.model_validate(row) for row in rows],
        total=total,
        page=page,
        size=size,
    )


# NOTE: declared BEFORE "/{employee_id}", otherwise "stats" would be read as an id.
@router.get("/stats", response_model=EmployeeStats)
def get_employee_stats(
    db: DbSession,
    current_user: EmployeeReader,  # session required (401) and role check (403)
) -> EmployeeStats:
    """HU-6.1: totals computed by the database in a single query."""
    row = db.execute(
        select(
            func.count(Employee.id),
            func.count(Employee.id).filter(Employee.status == EmployeeStatus.ACTIVO),
            func.count(Employee.id).filter(Employee.status == EmployeeStatus.INACTIVO),
        )
    ).one()
    return EmployeeStats(total=row[0], active=row[1], inactive=row[2])


def _count_active_by(
    db: Session, column: InstrumentedAttribute[str]
) -> list[CountItem]:
    """Active employees per distinct value of `column`, biggest group first."""
    total = func.count(Employee.id)
    rows = db.execute(
        select(column, total)
        .where(Employee.status == EmployeeStatus.ACTIVO)
        .group_by(column)
        .order_by(total.desc(), column)  # the column breaks ties: a stable order
    ).all()
    return [CountItem(name=name, count=count) for name, count in rows]


def _group_rest(items: list[CountItem], limit: int) -> list[CountItem]:
    """Keep the `limit` biggest groups and fold the rest into a single "Otros" bar.

    `items` arrive sorted from the biggest group to the smallest. A single left-over
    group keeps its own name: a bar called "Otros" that hides one position would mislead.
    """
    if len(items) <= limit + 1:
        return items
    rest = items[limit:]
    return [
        *items[:limit],
        CountItem(name=OTHERS_LABEL, count=sum(i.count for i in rest)),
    ]


def _summary(employee: Employee, event_date: date | None) -> PersonSummary:
    return PersonSummary(
        id=employee.id,
        first_names=employee.first_names,
        last_names=employee.last_names,
        position=employee.position,
        area=employee.area,
        event_date=event_date,
    )


# NOTE: declared BEFORE "/{employee_id}", otherwise "overview" would be read as an id.
@router.get("/overview", response_model=EmployeeOverview)
def get_employee_overview(
    db: DbSession,
    current_user: EmployeeReader,  # session required (401) and role check (403)
) -> EmployeeOverview:
    """HU-6.1: distributions and recent movements for the dashboard charts."""
    hires = db.scalars(
        select(Employee)
        .where(
            Employee.status == EmployeeStatus.ACTIVO,
            Employee.start_date
            <= func.current_date(),  # not hires that have not started
        )
        .order_by(Employee.start_date.desc(), Employee.created_at.desc(), Employee.id)
        .limit(RECENT_LIMIT)
    ).all()
    departures = db.scalars(
        select(Employee)
        .where(Employee.status == EmployeeStatus.INACTIVO)
        # A missing end date goes last: those departures have no date to sort by.
        .order_by(
            Employee.end_date.desc().nulls_last(), Employee.last_names, Employee.id
        )
        .limit(RECENT_LIMIT)
    ).all()
    return EmployeeOverview(
        by_area=_count_active_by(db, Employee.area),
        by_position=_group_rest(
            _count_active_by(db, Employee.position), POSITIONS_SHOWN
        ),
        recent_hires=[_summary(e, e.start_date) for e in hires],
        recent_departures=[_summary(e, e.end_date) for e in departures],
    )


def get_employee_or_404(db: Session, employee_id: uuid.UUID) -> Employee:
    employee = db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )
    return employee


@router.get("/{employee_id}", response_model=EmployeeDetailResponse)
def get_employee(
    employee_id: uuid.UUID,  # a malformed id is rejected with 422 before reaching us
    db: DbSession,
    current_user: EmployeeReader,  # session required (401) and role check (403)
) -> EmployeeDetailResponse:
    """HU-2.3: full record of one employee (any status, INACTIVO included)."""
    employee = get_employee_or_404(db, employee_id)
    account_id = db.scalar(select(User.id).where(User.employee_id == employee.id))
    return EmployeeDetailResponse(
        **EmployeeResponse.model_validate(employee).model_dump(),
        has_account=account_id is not None,
    )


@router.get("/{employee_id}/photo")
def get_employee_photo(
    employee_id: uuid.UUID,
    db: DbSession,
    current_user: EmployeeReader,  # session required (401) and role check (403)
    storage: Storage,
) -> Response:
    """HU-2.7: the private photo, only through the API and after the role check."""
    return photo_response(get_employee_or_404(db, employee_id), storage)


@router.post("/{employee_id}/account/reset-password", response_model=AccountCreated)
def reset_account_password(
    employee_id: uuid.UUID,
    request: Request,
    db: DbSession,
    current_user: Admin,  # session required (401) and ADMIN role (403)
) -> AccountCreated:
    """HU-1.5: replace a forgotten password with a new temporary one.

    It also restores access for a rehired employee: rehiring does not reopen the
    account by itself, that decision belongs to an administrator (HU-3.1).
    """
    employee = get_employee_or_404(db, employee_id)
    account = db.scalar(select(User).where(User.employee_id == employee.id))
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This employee has no access account",
        )
    if account.id == current_user.id:
        # A reset would lock the admin out of their own session in mid-action.
        raise conflict("account", "Use the change password option for your own account")
    if employee.status is not EmployeeStatus.ACTIVO:
        raise conflict("status", "An inactive employee cannot have access")

    temporary_password = generate_temporary_password()
    changes: dict[str, tuple[object, object]] = {
        "must_change_password": (account.must_change_password, True)
    }
    if not account.is_active:
        changes["is_active"] = (False, True)

    account.hashed_password = hash_password(temporary_password)  # the old one is gone
    account.must_change_password = True
    account.is_active = True
    account.token_version += 1  # open sessions die with the old password
    record_audit(
        db,
        actor=current_user,
        request=request,
        action=AuditAction.PASSWORD_RESET,
        entity_type="user",
        entity_id=account.id,
        changes=changes,
    )
    db.commit()

    return AccountCreated(
        email=account.email,
        role=account.role,
        temporary_password=temporary_password,
        must_change_password=True,
    )
