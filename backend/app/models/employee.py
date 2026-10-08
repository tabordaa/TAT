"""Employee record (HU-2.1). Not a login account: see app.models.user."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
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
        # Business rule enforced by the DATABASE (the only place that can
        # guarantee it, even with two simultaneous requests).
        UniqueConstraint("document_type", "document_number", name="uq_employees_document"),
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
    email: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(30))

    # Employment data
    position: Mapped[str] = mapped_column(String(120))
    area: Mapped[str | None] = mapped_column(String(120))
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
