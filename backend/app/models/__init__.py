"""Import every model here so Alembic's autogenerate can see it."""

from app.models.audit_log import AuditAction, AuditLog
from app.models.employee import (
    ContractType,
    DocumentType,
    Employee,
    EmployeeStatus,
    EmploymentContract,
)
from app.models.holiday import Holiday
from app.models.salary_change import SalaryChange
from app.models.user import User, UserRole
from app.models.vacation import VacationRequest, VacationStatus

__all__ = [
    "AuditAction",
    "AuditLog",
    "ContractType",
    "DocumentType",
    "Employee",
    "EmployeeStatus",
    "EmploymentContract",
    "Holiday",
    "SalaryChange",
    "User",
    "UserRole",
    "VacationRequest",
    "VacationStatus",
]
