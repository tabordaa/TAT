"""Writes the audit trail (HU-5.1)."""

import enum
import uuid
from collections.abc import Mapping
from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.network import client_ip
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User

# Fragments that must never name an audited field. A hit is a programming error,
# so it fails loudly (and in the tests) instead of quietly storing a secret.
_SECRET_FRAGMENTS = ("password", "token", "secret", "hash")


def _as_text(value: Any) -> str | None:
    """Audit values as text, so Decimal, date and enums all read the same."""
    if value is None:
        return None
    if isinstance(value, enum.Enum):
        return str(value.value)
    return str(value)


def record_audit(
    db: Session,
    *,
    actor: User,
    request: Request,
    action: AuditAction,
    entity_type: str,
    entity_id: uuid.UUID,
    changes: Mapping[str, tuple[Any, Any]],
) -> None:
    """Add an audit row to the CURRENT transaction; the caller commits.

    Sharing the transaction is the point: a change and its record are saved
    together or not at all, so no change can happen without leaving a trace.
    `changes` maps each field to its (old, new) values.
    """
    for field in changes:
        if any(fragment in field.lower() for fragment in _SECRET_FRAGMENTS):
            raise ValueError(f"Refusing to audit a secret field: {field}")

    db.add(
        AuditLog(
            actor_id=actor.id,
            actor_email=actor.email,
            action=action.value,
            entity_type=entity_type,
            entity_id=entity_id,
            changes={
                field: {"old": _as_text(old), "new": _as_text(new)}
                for field, (old, new) in changes.items()
            },
            ip=client_ip(request),
        )
    )
