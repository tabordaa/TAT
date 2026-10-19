"""Reusable FastAPI dependencies (DB session, authenticated user, role checks)."""

import uuid
from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
    )


def resolve_user_from_cookie(request: Request, db: Session) -> User | None:
    """Return the user behind a VALID session cookie, or None.

    Valid means: cookie present, signature OK, not expired, user exists,
    user is active and the token version matches (not revoked by logout).
    """
    token = request.cookies.get(get_settings().cookie_name)
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(str(payload["sub"]))
        token_version = int(payload["ver"])
    except (jwt.InvalidTokenError, KeyError, ValueError, TypeError):
        return None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        return None
    # Revocation check: logout bumped the version -> old tokens stop working.
    if token_version != user.token_version:
        return None
    return user


def get_current_user(request: Request, db: DbSession) -> User:
    """Dependency for protected endpoints: the authenticated user or 401.

    Any endpoint just declares `user: CurrentUser` to require login.
    """
    user = resolve_user_from_cookie(request, db)
    if user is None:
        raise _unauthorized()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*allowed: UserRole) -> Callable[[User], User]:
    """Dependency factory: only users whose role is in `allowed` get through.

    - No valid session -> 401 (raised by get_current_user, which runs first).
    - Valid session but the wrong role -> 403.

    The 403 message is generic on purpose: it does not list which roles WOULD
    be accepted, so it tells an attacker nothing about the permission model.
    Usage: `user: Annotated[User, Depends(require_role(UserRole.ADMIN))]`.
    """
    allowed_roles = frozenset(allowed)

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return dependency


# Who may use the employee directory (it exposes salary and personal data).
# Conservative choice: MANAGER and EMPLOYEE get no access until the product
# decides what each of them may see.
HrStaff = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.HR))]
