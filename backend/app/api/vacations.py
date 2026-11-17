"""Vacations: balance (HU-4.3)."""

import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession, EmployeeReader
from app.api.employees import get_employee_or_404
from app.api.me import own_employee
from app.schemas.vacation import VacationBalanceResponse
from app.services.vacations import vacation_balance

router = APIRouter(tags=["vacations"])


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
