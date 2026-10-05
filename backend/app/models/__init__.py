"""Import every model here so Alembic's autogenerate can see it."""

from app.models.user import User, UserRole

__all__ = ["User", "UserRole"]
