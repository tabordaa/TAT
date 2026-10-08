"""Import every model here so Alembic's autogenerate can see it."""

from app.models.employee import ContractType, DocumentType, Employee, EmployeeStatus
from app.models.user import User, UserRole

__all__ = [
    "ContractType",
    "DocumentType",
    "Employee",
    "EmployeeStatus",
    "User",
    "UserRole",
]
