"""HU-2.1 Employee registration."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.employee import Employee, EmployeeStatus
from app.schemas.employee import EmployeeCreate, EmployeeResponse

router = APIRouter(prefix="/employees", tags=["employees"])

DUPLICATE_DOCUMENT = "An active employee with this document already exists"
DUPLICATE_EMAIL = "An active employee with this email already exists"

# Partial unique index name -> (field reported to the client, message).
_UNIQUE_VIOLATIONS = {
    "uq_employees_active_document": ("document_number", DUPLICATE_DOCUMENT),
    "uq_employees_active_email": ("email", DUPLICATE_EMAIL),
}


def _conflict(field: str, message: str) -> HTTPException:
    # Structured detail so the frontend can show the error under the right field.
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"field": field, "message": message},
    )


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    data: EmployeeCreate,
    db: DbSession,
    current_user: CurrentUser,  # requires a valid session (401 otherwise)
) -> Employee:
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
        raise _conflict("document_number", DUPLICATE_DOCUMENT)

    email_taken = db.scalar(select(Employee.id).where(active, Employee.email == email))
    if email_taken is not None:
        raise _conflict("email", DUPLICATE_EMAIL)

    employee = Employee(
        **data.model_dump(exclude={"document_number", "email"}),
        document_number=document_number,
        email=email,
        status=EmployeeStatus.ACTIVO,  # set by the server, never by the client
        created_by_id=current_user.id,  # audit trail
    )
    db.add(employee)

    # 2) The partial unique indexes are the real guarantee: if two requests
    #    pass the checks above at the same time, the database rejects one.
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        diag = getattr(exc.orig, "diag", None)
        constraint = getattr(diag, "constraint_name", None)
        if constraint in _UNIQUE_VIOLATIONS:
            raise _conflict(*_UNIQUE_VIOLATIONS[constraint]) from exc
        raise

    db.refresh(employee)
    return employee
