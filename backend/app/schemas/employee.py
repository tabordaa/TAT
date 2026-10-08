"""API contracts for employees (HU-2.1)."""

import uuid
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing_extensions import Self  # typing.Self needs Python 3.11+ (you're on 3.10)

from app.models.employee import (
    CONTRACTS_WITH_END_DATE,
    ContractType,
    DocumentType,
    EmployeeStatus,
)


class EmployeeCreate(BaseModel):
    """Input for registering an employee.

    `status` is intentionally NOT here: every new employee is ACTIVO and the
    client cannot choose otherwise (acceptance criterion 3).
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    first_names: str = Field(min_length=1, max_length=100)
    last_names: str = Field(min_length=1, max_length=100)
    document_type: DocumentType
    document_number: str = Field(pattern=r"^[A-Za-z0-9-]{4,20}$")
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)

    position: str = Field(min_length=1, max_length=120)
    area: str | None = Field(default=None, max_length=120)
    contract_type: ContractType
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        # Same rules as the frontend; the server is the one that counts.
        if self.contract_type in CONTRACTS_WITH_END_DATE and self.end_date is None:
            raise ValueError("end_date is required for this contract type")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_names: str
    last_names: str
    document_type: DocumentType
    document_number: str
    email: str | None
    phone: str | None
    position: str
    area: str | None
    contract_type: ContractType
    start_date: date
    end_date: date | None
    status: EmployeeStatus
    created_at: datetime
