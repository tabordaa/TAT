"""HU-2.1 Employee registration."""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.deps import CurrentUser, DbSession
from app.models.employee import Employee, EmployeeStatus
from app.schemas.employee import EmployeeCreate, EmployeeResponse

router = APIRouter(prefix="/employees", tags=["employees"])

DUPLICATE_DOCUMENT = "An employee with this document already exists"


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee(
    data: EmployeeCreate,
    db: DbSession,
    current_user: CurrentUser,  # requires a valid session (401 otherwise)
) -> Employee:
    document_number = data.document_number.upper()

    # 1) Friendly, fast check for the common case.
    exists = db.scalar(
        select(Employee.id).where(
            Employee.document_type == data.document_type,
            Employee.document_number == document_number,
        )
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_DOCUMENT)

    employee = Employee(
        **data.model_dump(exclude={"document_number", "email"}),
        document_number=document_number,
        email=str(data.email).lower() if data.email is not None else None,
        status=EmployeeStatus.ACTIVO,  # set by the server, never by the client
        created_by_id=current_user.id,  # audit trail
    )
    db.add(employee)

    # 2) The UNIQUE constraint is the real guarantee: if two requests pass the
    #    check above at the same time, the database rejects the second one.
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=DUPLICATE_DOCUMENT
        ) from exc

    db.refresh(employee)
    return employee
