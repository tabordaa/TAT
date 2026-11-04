"""Audit trail of critical changes (HU-5.1): who changed what, when, from where."""

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AuditAction(str, enum.Enum):
    EMPLOYEE_CREATED = "EMPLOYEE_CREATED"
    ACCOUNT_CREATED = "ACCOUNT_CREATED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET = "PASSWORD_RESET"
    CONTACT_UPDATED = "CONTACT_UPDATED"
    PHOTO_UPDATED = "PHOTO_UPDATED"
    CONTRACT_ASSIGNED = "CONTRACT_ASSIGNED"
    EMPLOYEE_REHIRED = "EMPLOYEE_REHIRED"
    CONTRACT_TERMINATED = "CONTRACT_TERMINATED"


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_created_at", "created_at", "id"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # SET NULL plus the email copy: the history must outlive the account.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    actor_email: Mapped[str] = mapped_column(String(255))
    # Plain text, no CHECK: a new action must not require a migration.
    action: Mapped[str] = mapped_column(String(40))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[uuid.UUID]
    # {"field": {"old": ..., "new": ...}}, values as text. Never secrets.
    changes: Mapped[dict[str, Any]] = mapped_column(JSONB)
    ip: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
