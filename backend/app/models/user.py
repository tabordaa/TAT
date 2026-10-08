"""User account that can sign in to TAT (HR staff), not an employee record."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    HR = "HR"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Always stored in lowercase (normalized in the service layer).
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(
        # VARCHAR + CHECK instead of a native Postgres ENUM: easier to migrate.
        Enum(
            UserRole,
            name="user_role",
            native_enum=False,
            create_constraint=True,
            length=20,
        ),
        default=UserRole.HR,
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    # Incremented on logout. Every JWT carries the version it was issued with
    # ("ver" claim); tokens with an older version are rejected -> real revocation.
    token_version: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
