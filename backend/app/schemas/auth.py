"""API contracts for authentication (what goes in and out over HTTP)."""

import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    # No complexity rules on login: those belong to registration/password change.
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    """Public view of a user. Never includes hashed_password."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    full_name: str
    role: UserRole
