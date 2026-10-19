"""API contracts for employees (HU-2.1)."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing_extensions import Self  # typing.Self needs Python 3.11+ (you're on 3.10)

from app.models.employee import (
    CONTRACTS_WITH_END_DATE,
    ContractType,
    DocumentType,
    EmployeeStatus,
)
from app.models.user import UserRole


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
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)

    position: str = Field(min_length=1, max_length=120)
    area: str = Field(min_length=1, max_length=120)
    # Decimal (not float) so cents are exact; serialized as a JSON string.
    salary: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    contract_type: ContractType
    start_date: date
    end_date: date | None = None

    # Optional (HU-1.4): also create a login account with this role. Only an
    # ADMIN may use it; the server generates the temporary password.
    account_role: UserRole | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        # Same rules as the frontend; the server is the one that counts.
        if self.contract_type in CONTRACTS_WITH_END_DATE and self.end_date is None:
            raise ValueError("end_date is required for this contract type")
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date cannot be before start_date")
        return self


class EmployeeListItem(BaseModel):
    """Row of the employee directory (HU-2.2).

    Deliberately WITHOUT salary or email: a directory shows the minimum needed
    to find someone. The detail view (HU-2.3) shows the full record.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_names: str
    last_names: str
    document_type: DocumentType
    document_number: str
    position: str
    area: str
    start_date: date
    status: EmployeeStatus


class EmployeeListResponse(BaseModel):
    items: list[EmployeeListItem]
    total: int  # rows matching the filters, across ALL pages
    page: int
    size: int


class EmployeeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_names: str
    last_names: str
    document_type: DocumentType
    document_number: str
    email: str
    phone: str | None
    position: str
    area: str
    salary: Decimal
    contract_type: ContractType
    start_date: date
    end_date: date | None
    status: EmployeeStatus
    created_at: datetime


class AccountCreated(BaseModel):
    """The login account created together with an employee (HU-1.4).

    `temporary_password` is in plain text only in this one response: the
    database keeps just its hash, so it can never be shown again.
    """

    email: str
    role: UserRole
    temporary_password: str
    must_change_password: bool


class EmployeeCreatedResponse(EmployeeResponse):
    """Response of POST /employees: the employee plus the optional new account."""

    account: AccountCreated | None = None
