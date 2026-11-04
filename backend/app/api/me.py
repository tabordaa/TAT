"""HU-2.6: what the signed-in person can see about themselves.

These routes take no employee id. The record always comes from the session, so
there is no parameter a user could change to reach someone else's data (IDOR).
"""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.employee import Employee
from app.schemas.employee import EmployeeResponse

router = APIRouter(prefix="/me", tags=["me"])


def _own_employee(user: CurrentUser, db: DbSession) -> Employee:
    # An account may exist without a record, like the first administrator.
    employee = db.get(Employee, user.employee_id) if user.employee_id else None
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This account is not linked to an employee record",
        )
    return employee


@router.get("/employee", response_model=EmployeeResponse)
def get_my_employee(current_user: CurrentUser, db: DbSession) -> Employee:
    return _own_employee(current_user, db)
