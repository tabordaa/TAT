"""HU-1.1 Login, HU-1.3 Logout and the current-session endpoint."""

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _invalid_credentials() -> HTTPException:
    # Same message for "email not found" and "wrong password":
    # never tell an attacker which emails exist (user enumeration).
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )


@router.post("/login", response_model=UserResponse)
def login(credentials: LoginRequest, response: Response, db: DbSession) -> User:
    settings = get_settings()
    email = credentials.email.lower()

    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(credentials.password, DUMMY_HASH)  # constant-time path
        raise _invalid_credentials()
    if not verify_password(credentials.password, user.hashed_password):
        raise _invalid_credentials()
    if not user.is_active:
        raise _invalid_credentials()

    token = create_access_token(subject=str(user.id), role=user.role.value)

    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,  # JavaScript cannot read it -> mitigates token theft via XSS
        secure=settings.cookie_secure,  # HTTPS only in production
        samesite="lax",  # not sent on cross-site POSTs -> mitigates CSRF
        path="/",
    )
    # response_model=UserResponse filters the ORM object: no hashed_password.
    return user


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> User:
    """Lets the frontend ask "who am I?" since it cannot read the cookie."""
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    settings = get_settings()
    # Attributes must match the ones used in set_cookie or the browser keeps it.
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
