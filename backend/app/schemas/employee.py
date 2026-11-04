"""API contracts for employees (HU-2.1)."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing_extensions import Self  # typing.Self needs Python 3.11+ (you're on 3.10)

from app.models.employee import (
    CONTRACTS_WITH_END_DATE,
    ContractType,
    DocumentType,
    EmployeeStatus,
)
from app.models.user import UserRole


def _check_contract_dates(
    contract_type: ContractType, start_date: date, end_date: date | None
) -> None:
    # Same rules as the frontend; the server is the one that counts.
    if contract_type in CONTRACTS_WITH_END_DATE and end_date is None:
        raise ValueError("end_date is required for this contract type")
    if contract_type not in CONTRACTS_WITH_END_DATE and end_date is not None:
        raise ValueError("end_date must be empty for this contract type")
    if end_date is not None and end_date < start_date:
        raise ValueError("end_date cannot be before start_date")


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
        _check_contract_dates(self.contract_type, self.start_date, self.end_date)
        return self


class ContractAssign(BaseModel):
    """HU-3.1: a new contract. For an INACTIVO employee it is also the rehire."""

    model_config = ConfigDict(extra="forbid")

    contract_type: ContractType
    start_date: date
    end_date: date | None = None

    @model_validator(mode="after")
    def _check_dates(self) -> Self:
        _check_contract_dates(self.contract_type, self.start_date, self.end_date)
        return self


class ContractTerminate(BaseModel):
    """HU-3.3: the employee's departure date."""

    model_config = ConfigDict(extra="forbid")

    end_date: date


class ContractAlert(BaseModel):
    """HU-3.2: a contract that needs attention. No salary or document."""

    id: uuid.UUID  # the employee, to link to their record
    first_names: str
    last_names: str
    position: str
    end_date: date
    days_left: int  # calculated by the server; negative once it has expired
    state: Literal["POR_VENCER", "VENCIDO"]


class ContractResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    contract_type: ContractType
    start_date: date
    end_date: date | None
    terminated_on: date | None


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
    address: str | None
    has_photo: bool
    position: str
    area: str
    salary: Decimal
    contract_type: ContractType
    start_date: date
    end_date: date | None
    status: EmployeeStatus
    created_at: datetime


class ContactUpdate(BaseModel):
    """HU-2.7: the only fields employees may change about themselves.

    extra="forbid" answers 422 to anything else, such as salary or position.
    A field left out stays as it is; an explicit null clears it.
    """

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    phone: str | None = Field(default=None, pattern=r"^\+?[0-9 ()-]{7,30}$")
    address: str | None = Field(default=None, min_length=1, max_length=200)


class EmployeeDetailResponse(EmployeeResponse):
    """Response of GET /employees/{id}: also says whether a login account exists."""

    has_account: bool


class AccountCreated(BaseModel):
    """A login account with a fresh temporary password (HU-1.4 and HU-1.5).

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


class CountItem(BaseModel):
    """One bar of a distribution chart: a label and how many employees it groups."""

    name: str
    count: int


class PersonSummary(BaseModel):
    """A row of the dashboard's "recent" lists. No salary, document or email."""

    id: uuid.UUID
    first_names: str
    last_names: str
    position: str
    area: str
    # Hires: start date. Departures: contract end date (None if it was never set).
    event_date: date | None


class EmployeeOverview(BaseModel):
    """What the dashboard draws below the headline numbers (HU-6.1)."""

    by_area: list[CountItem]  # active employees per area, biggest first
    by_position: list[CountItem]  # active employees per position, long tail grouped
    recent_hires: list[PersonSummary]
    recent_departures: list[PersonSummary]


class EmployeeStats(BaseModel):
    """Headline numbers for the dashboard (HU-6.1)."""

    total: int  # every employee ever registered (history included)
    active: int
    inactive: int
