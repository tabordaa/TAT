"""HU-1.1 Login, HU-1.3 Logout and the current-session endpoint."""

import hashlib
import logging

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, resolve_user_from_cookie
from app.core.config import get_settings
from app.core.network import client_ip
from app.core.rate_limit import LoginThrottle
from app.core.security import (
    DUMMY_HASH,
    create_access_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])

logger = logging.getLogger("tat.auth")

_settings = get_settings()
login_throttle = LoginThrottle(
    account_failures=_settings.login_max_failures_per_account,
    ip_failures=_settings.login_max_failures_per_ip,
    window_seconds=_settings.login_failure_window_seconds,
)


def _invalid_credentials() -> HTTPException:
    # Same message for "email not found" and "wrong password":
    # never tell an attacker which emails exist (user enumeration).
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )


def _email_reference(email: str) -> str:
    # Enough to correlate attempts in the logs without storing the address:
    # people also type their password into the email field by mistake.
    return hashlib.sha256(email.encode()).hexdigest()[:12]


def _authenticate(email: str, password: str, db: DbSession) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(password, DUMMY_HASH)  # constant-time path
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


@router.post("/login", response_model=UserResponse)
def login(
    credentials: LoginRequest, request: Request, response: Response, db: DbSession
) -> User:
    settings = get_settings()
    email = credentials.email.lower()
    ip = client_ip(request)

    # Checked before hashing: a blocked attacker must not consume Argon2 time.
    # It never reveals whether the email exists: unknown ones count the same.
    retry_after = login_throttle.retry_after(ip, email)
    if retry_after > 0:
        logger.warning(
            "login blocked ip=%s email_ref=%s retry_after=%s",
            ip,
            _email_reference(email),
            retry_after,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user = _authenticate(email, credentials.password, db)
    if user is None:
        login_throttle.record_failure(ip, email)
        logger.warning("login failed ip=%s email_ref=%s", ip, _email_reference(email))
        raise _invalid_credentials()
    login_throttle.record_success(ip, email)

    token = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        version=user.token_version,
    )

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
def logout(request: Request, response: Response, db: DbSession) -> None:
    """HU-1.3: invalidate the token on the server AND remove the cookie.

    Idempotent: calling it without a valid session still returns 204.
    """
    user = resolve_user_from_cookie(request, db)
    if user is not None:
        # Every token issued before this moment now has an outdated "ver".
        # Side effect (accepted): it closes the session on all devices.
        user.token_version += 1
        db.commit()

    settings = get_settings()
    # Attributes must match the ones used in set_cookie or the browser keeps it.
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )
