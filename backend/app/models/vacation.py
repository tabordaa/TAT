"""Vacation requests (HU-4.1 to 4.4). The balance is never stored: see app.services.vacations."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VacationStatus(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    APROBADA = "APROBADA"
    RECHAZADA = "RECHAZADA"
    CANCELADA = "CANCELADA"


class VacationRequest(Base):
    __tablename__ = "vacation_requests"
    __table_args__ = (
        Index("ix_vacation_requests_employee_status", "employee_id", "status"),
        Index("ix_vacation_requests_status_start", "status", "start_date"),
        CheckConstraint("end_date >= start_date", name="ck_vacation_requests_dates"),
        CheckConstraint("business_days > 0", name="ck_vacation_requests_business_days"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT")
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    # Monday to Friday between both dates, computed by the server when requested.
    business_days: Mapped[int]
    status: Mapped[VacationStatus] = mapped_column(
        Enum(
            VacationStatus,
            name="vacation_status",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default=VacationStatus.PENDIENTE,
    )
    # Why it was rejected or cancelled (HU-4.2). Never a secret.
    reason: Mapped[str | None] = mapped_column(String(500))
    requested_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    decided_by_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
