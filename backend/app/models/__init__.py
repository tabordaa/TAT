"""Import every model here so Alembic's autogenerate can see it."""

from app.models.audit_log import AuditAction, AuditLog
from app.models.employee import (
    ContractType,
    DocumentType,
    Employee,
    EmployeeStatus,
    EmploymentContract,
)
from app.models.user import User, UserRole

__all__ = [
    "AuditAction",
    "AuditLog",
    "ContractType",
    "DocumentType",
    "Employee",
    "EmployeeStatus",
    "EmploymentContract",
    "User",
    "UserRole",
]
