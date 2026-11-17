"""Salary history (HU-2.4 writes it, HU-2.5 shows it)."""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SalaryChange(Base):
    """One salary change. Rows are only ever inserted, never updated.

    `employees.salary` holds the current value; this table keeps every step so
    a raise never erases the previous figure.
    """

    __tablename__ = "salary_changes"
    __table_args__ = (
        Index("ix_salary_changes_employee_changed", "employee_id", "changed_at"),
        CheckConstraint(
            "old_salary > 0 AND new_salary > 0", name="ck_salary_changes_positive"
        ),
        # A row exists because the salary really changed.
        CheckConstraint("old_salary <> new_salary", name="ck_salary_changes_differs"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT")
    )
    # Same type as employees.salary: exact cents, never a float.
    old_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    new_salary: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    changed_by_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
