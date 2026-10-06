"""Reusable FastAPI dependencies (DB session, authenticated user)."""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def get_current_user(request: Request, db: DbSession) -> User:
    """Read the JWT from the HttpOnly cookie and load the user it belongs to.

    Any protected endpoint just declares `user: CurrentUser` to require login.
    """
    token = request.cookies.get(get_settings().cookie_name)
    if not token:
        raise _unauthorized()

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
    except (jwt.InvalidTokenError, KeyError, ValueError) as exc:
        raise _unauthorized() from exc

    user = db.get(User, user_id)
    # A deactivated user must lose access even if their token is still valid.
    if user is None or not user.is_active:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
