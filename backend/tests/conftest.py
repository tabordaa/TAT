"""Test environment: safety guard, DB isolation and shared fixtures.

IMPORTANT: the guard below runs at import time, BEFORE the app is imported,
because `app.db.session` builds its engine from the environment on import.
"""

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_TEST_FILE = BACKEND_DIR / ".env.test"
ENV_FILE = BACKEND_DIR / ".env"


def _load_test_environment() -> None:
    """Load .env.test into os.environ or refuse to run.

    Real environment variables win over the .env file in pydantic-settings, so
    exporting these values is enough to point the whole app at the test setup.
    """
    if not ENV_TEST_FILE.exists():
        raise pytest.UsageError(
            "backend/.env.test not found. Copy the template and set DATABASE_URL."
        )

    test_values = dotenv_values(ENV_TEST_FILE)
    test_url = test_values.get("DATABASE_URL")
    if not test_url:
        raise pytest.UsageError("DATABASE_URL is missing in backend/.env.test")
    if test_values.get("ENVIRONMENT", "development") == "production":
        raise pytest.UsageError("Refusing to run tests with ENVIRONMENT=production")

    # Sprint 2 exception: tests share the development database. It is allowed
    # ONLY when the flag is set explicitly. Once a separate tat-test project
    # exists, its URL differs from .env and the flag is no longer needed.
    dev_url = dotenv_values(ENV_FILE).get("DATABASE_URL") if ENV_FILE.exists() else None
    uses_dev_db = dev_url is not None and test_url == dev_url
    allowed = str(test_values.get("ALLOW_TESTS_ON_DEV_DB", "")).lower() == "true"
    if uses_dev_db and not allowed:
        raise pytest.UsageError(
            "DATABASE_URL in .env.test is the development database. "
            "Set ALLOW_TESTS_ON_DEV_DB=true in .env.test to accept it explicitly."
        )

    for key, value in test_values.items():
        if value is not None:
            os.environ[key.upper()] = value


_load_test_environment()

# App imports must come AFTER the guard (see module docstring).
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import engine as app_engine
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole

TEST_PASSWORD = "Test-Password-123!"


@pytest.fixture(scope="session")
def engine() -> Engine:
    return app_engine


@pytest.fixture(scope="session")
def password_hash() -> str:
    # Argon2 is deliberately slow: hash once per run, not once per test.
    return hash_password(TEST_PASSWORD)


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """A session whose changes are ALWAYS rolled back after the test.

    The outer transaction is never committed. The app's own `commit()` only
    releases a SAVEPOINT (join_transaction_mode="create_savepoint"), so the
    test sees its data but nothing is ever persisted. We never TRUNCATE or
    DELETE: rollback is the only cleanup.
    """
    connection = engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    """TestClient whose requests use the test session instead of a new one."""

    def _override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def make_user(
    db: Session,
    password_hash: str,
    role: UserRole = UserRole.HR,
    is_active: bool = True,
) -> User:
    """Insert a user with a unique email (random suffix) and return it."""
    user = User(
        email=f"test-{uuid.uuid4().hex[:12]}@tat-test.example.com",
        full_name="Test User",
        hashed_password=password_hash,
        role=role,
        is_active=is_active,
    )
    db.add(user)
    db.commit()  # only releases the SAVEPOINT (see `db` fixture)
    return user


@pytest.fixture
def hr_user(db: Session, password_hash: str) -> User:
    return make_user(db, password_hash, UserRole.HR)


@pytest.fixture
def auth_client(client: TestClient, hr_user: User) -> TestClient:
    """A client already logged in as an HR user (cookie stored in the client)."""
    response = client.post(
        "/auth/login", json={"email": hr_user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return client


def employee_payload(**overrides: Any) -> dict[str, Any]:
    """A valid POST /employees body with unique document and email."""
    suffix = uuid.uuid4().hex[:10]
    payload: dict[str, Any] = {
        "first_names": "Ana",
        "last_names": "Prueba",
        "document_type": "CC",
        "document_number": f"T{suffix}",
        "email": f"emp-{suffix}@tat-test.example.com",
        "phone": None,
        "position": "Analista",
        "area": "Tecnologia",
        "salary": "3500000.00",
        "contract_type": "INDEFINIDO",
        "start_date": "2026-01-15",
        "end_date": None,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def make_employee_payload() -> Any:
    return employee_payload


def cookie_name() -> str:
    return get_settings().cookie_name
