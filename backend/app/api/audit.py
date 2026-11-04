"""HU-5.1: the audit trail, readable only by administrators."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import Admin, DbSession
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogItem, AuditLogListResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    db: DbSession,
    current_user: Admin,  # session required (401) and ADMIN role (403)
    page: Annotated[int, Query(ge=1, le=100_000)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AuditLogListResponse:
    total = db.scalar(select(func.count()).select_from(AuditLog)) or 0
    rows = db.scalars(
        select(AuditLog)
        # Newest first; id breaks ties so pages never repeat or skip rows.
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * size)
        .limit(size)
    ).all()
    return AuditLogListResponse(
        items=[AuditLogItem.model_validate(row) for row in rows],
        total=total,
        page=page,
        size=size,
    )
