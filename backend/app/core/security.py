"""Password hashing (Argon2) and JWT creation/verification."""

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

# Argon2id with the library's recommended parameters.
password_hash = PasswordHash.recommended()

# Used when the email does not exist, so a failed login always takes the same
# time. Otherwise an attacker could measure response times to discover which
# emails are registered (user enumeration via timing attack).
DUMMY_HASH = password_hash.hash("timing-attack-dummy-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str, role: str) -> str:
    """Signed (NOT encrypted) token: never put sensitive data in the payload."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Raises jwt.InvalidTokenError if the token is expired, tampered or malformed.

    The caller decides how to respond (401); this function only verifies.
    """
    settings = get_settings()
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.jwt_secret_key.get_secret_value(),
        # Explicit allow-list: blocks "alg": "none" / algorithm confusion attacks.
        algorithms=[settings.jwt_algorithm],
        options={"require": ["exp", "iat", "sub"]},
    )
    return payload
