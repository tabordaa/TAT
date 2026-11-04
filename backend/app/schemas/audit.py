"""API contracts for the audit trail (HU-5.1)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FieldChange(BaseModel):
    old: str | None
    new: str | None


class AuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    actor_email: str
    action: str
    entity_type: str
    entity_id: uuid.UUID
    changes: dict[str, FieldChange]
    ip: str
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogItem]
    total: int
    page: int
    size: int
