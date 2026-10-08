"""Employee record (HU-2.1). Not a login account: see app.models.user."""

import enum
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DocumentType(str, enum.Enum):
    CC = "CC"  # Cédula de ciudadanía
    CE = "CE"  # Cédula de extranjería
    PA = "PA"  # Pasaporte
    PPT = "PPT"  # Permiso por Protección Temporal


class ContractType(str, enum.Enum):
    INDEFINIDO = "INDEFINIDO"
    FIJO = "FIJO"
    OBRA_LABOR = "OBRA_LABOR"
    APRENDIZAJE = "APRENDIZAJE"


# Contracts that legally have an end date.
CONTRACTS_WITH_END_DATE = frozenset(
    {ContractType.FIJO, ContractType.OBRA_LABOR, ContractType.APRENDIZAJE}
)


class EmployeeStatus(str, enum.Enum):
    ACTIVO = "ACTIVO"
    INACTIVO = "INACTIVO"


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    return Enum(enum_cls, name=name, native_enum=False, create_constraint=True, length=20)


class Employee(Base):
    __tablename__ = "employees"
    __table_args__ = (
        # Business rules enforced by the DATABASE (the only place that can
        # guarantee them, even with two simultaneous requests). They are
        # PARTIAL unique indexes: only ACTIVO employees must be unique, so an
        # INACTIVO record does not block a rehire (HU-3.1).
        Index(
            "uq_employees_active_document",
            "document_type",
            "document_number",
            unique=True,
            postgresql_where=text("status = 'ACTIVO'"),
        ),
        Index(
            "uq_employees_active_email",
            "email",
            unique=True,
            postgresql_where=text("status = 'ACTIVO'"),
        ),
        CheckConstraint("salary > 0", name="ck_employees_salary_positive"),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_employees_end_after_start",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # Personal data
    first_names: Mapped[str] = mapped_column(String(100))
    last_names: Mapped[str] = mapped_column(String(100))
    document_type: Mapped[DocumentType] = mapped_column(_enum(DocumentType, "document_type"))
    document_number: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255))  # stored lowercase
    phone: Mapped[str | None] = mapped_column(String(30))

    # Employment data
    position: Mapped[str] = mapped_column(String(120))
    area: Mapped[str] = mapped_column(String(120))
    # Money is never a float: NUMERIC keeps exact cents.
    salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    contract_type: Mapped[ContractType] = mapped_column(_enum(ContractType, "contract_type"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[EmployeeStatus] = mapped_column(
        _enum(EmployeeStatus, "employee_status"),
        default=EmployeeStatus.ACTIVO,
        server_default=EmployeeStatus.ACTIVO.value,
    )

    # Audit trail: who registered this employee and when.
    created_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
