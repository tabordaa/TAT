"""API contracts for vacations (HU-4.1 to 4.4)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from app.models.vacation import VacationStatus
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


class VacationRequestCreate(BaseModel):
    """HU-4.1: only the dates. Business days, status and who asked are decided
    by the server, so the client cannot send them (extra="forbid")."""

    model_config = ConfigDict(extra="forbid")

    start_date: date
    end_date: date

    @model_validator(mode="after")
    def end_not_before_start(self) -> Self:
        if self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class VacationRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    start_date: date
    end_date: date
    business_days: int
    status: VacationStatus
    reason: str | None
    created_at: datetime
    decided_at: datetime | None
