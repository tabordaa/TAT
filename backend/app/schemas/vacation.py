"""API contracts for vacations (HU-4.1 to 4.4)."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from app.services.vacations import DAYS_PER_YEAR, VacationBalance


class VacationBalanceResponse(BaseModel):
    """HU-4.3: the days an employee has, calculated on every read."""

    days_per_year: int
    contract_start: date | None  # None: no contract in force, everything is 0
    accrued_days: Decimal
    used_days: int
    pending_days: int
    available_days: Decimal
    requestable_days: Decimal

    @classmethod
    def of(cls, balance: VacationBalance) -> "VacationBalanceResponse":
        return cls(
            days_per_year=DAYS_PER_YEAR,
            contract_start=balance.contract_start,
            accrued_days=balance.accrued,
            used_days=balance.used,
            pending_days=balance.pending,
            available_days=balance.available,
            requestable_days=balance.requestable,
        )
