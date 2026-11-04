"""HU-1.2 Forced password change on first access."""

import logging
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.main import app
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, cookie_name, make_user

NEW_PASSWORD = "Brand-New-Password-1"
LOCKED_CODE = "PASSWORD_CHANGE_REQUIRED"


def _login(client: TestClient, email: str, password: str = TEST_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _change(client: TestClient, current: str = TEST_PASSWORD, new: str = NEW_PASSWORD):
    return client.post(
        "/auth/change-password",
        json={"current_password": current, "new_password": new},
    )


@pytest.fixture
def pending_user(db: Session, password_hash: str) -> User:
    """An ADMIN still on a temporary password: every role check would pass."""
    return make_user(db, password_hash, UserRole.ADMIN, must_change_password=True)


@pytest.fixture
def pending_client(client: TestClient, pending_user: User) -> TestClient:
    assert _login(client, pending_user.email).status_code == 200
    return client


# --- CA01 and CA04: nothing else is reachable until the password changes -------


def test_login_with_a_temporary_password_reports_the_pending_change(
    client: TestClient, pending_user: User
) -> None:
    response = _login(client, pending_user.email)
    assert response.status_code == 200
    assert response.json()["must_change_password"] is True


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/employees"),
        ("GET", "/employees/stats"),
        ("GET", "/employees/overview"),
        ("GET", "/employees/00000000-0000-0000-0000-000000000000"),
        ("POST", "/employees"),
        ("GET", "/audit"),
    ],
)
def test_other_endpoints_are_locked(
    pending_client: TestClient, method: str, path: str
) -> None:
    response = pending_client.request(method, path)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == LOCKED_CODE


def test_no_route_forgets_the_lock(pending_client: TestClient) -> None:
    # Walks the published API, so a future endpoint is covered automatically.
    # A placeholder id is fine: the lock must answer before any validation.
    fake_id = "00000000-0000-0000-0000-000000000000"
    checked = 0
    for path, operations in app.openapi()["paths"].items():
        if path.startswith(("/health", "/auth/")):
            continue
        url = re.sub(r"\{[^}]+\}", fake_id, path)
        for method in operations:
            response = pending_client.request(method.upper(), url)
            assert response.status_code == 403, f"{method} {path}"
            checked += 1
    assert checked >= 5


def test_who_am_i_still_works(pending_client: TestClient) -> None:
    assert pending_client.get("/auth/me").status_code == 200


def test_logout_still_works(pending_client: TestClient) -> None:
    assert pending_client.post("/auth/logout").status_code == 204


def test_a_new_session_does_not_skip_the_lock(
    client: TestClient, pending_user: User
) -> None:
    _login(client, pending_user.email)
    client.post("/auth/logout")
    _login(client, pending_user.email)
    assert client.get("/employees").status_code == 403


def test_everything_opens_after_the_change(pending_client: TestClient) -> None:
    response = _change(pending_client)

    assert response.status_code == 200
    assert response.json()["must_change_password"] is False
    assert pending_client.get("/employees").status_code == 200
    assert pending_client.get("/auth/me").json()["must_change_password"] is False


# --- CA02 and CA03: rules for the new password ---------------------------------


@pytest.mark.parametrize("new", ["", "short", "1234567"])
def test_new_password_needs_eight_characters(
    pending_client: TestClient, new: str
) -> None:
    assert _change(pending_client, new=new).status_code == 422


def test_exactly_eight_characters_are_accepted(pending_client: TestClient) -> None:
    assert _change(pending_client, new="12345678").status_code == 200


def test_very_long_password_is_rejected(pending_client: TestClient) -> None:
    assert _change(pending_client, new="x" * 129).status_code == 422


def test_new_password_cannot_equal_the_temporary_one(
    pending_client: TestClient,
) -> None:
    response = _change(pending_client, new=TEST_PASSWORD)

    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "new_password"
    assert pending_client.get("/employees").status_code == 403


def test_wrong_current_password_changes_nothing(
    pending_client: TestClient, pending_user: User
) -> None:
    response = _change(pending_client, current="not-the-password")

    assert response.status_code == 400
    assert response.json()["detail"]["field"] == "current_password"
    assert verify_password(TEST_PASSWORD, pending_user.hashed_password)
    assert pending_user.must_change_password is True


def test_guessing_the_current_password_gets_blocked(
    pending_client: TestClient,
) -> None:
    for _ in range(5):
        assert _change(pending_client, current="wrong-guess").status_code == 400

    response = _change(pending_client)

    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) > 0


def test_extra_fields_are_rejected(pending_client: TestClient) -> None:
    response = pending_client.post(
        "/auth/change-password",
        json={
            "current_password": TEST_PASSWORD,
            "new_password": NEW_PASSWORD,
            "must_change_password": False,
        },
    )
    assert response.status_code == 422


def test_requires_a_session(client: TestClient) -> None:
    assert _change(client).status_code == 401


# --- effects of a successful change --------------------------------------------


def test_only_the_new_password_opens_the_account(
    client: TestClient, pending_user: User
) -> None:
    _login(client, pending_user.email)
    _change(client)
    client.post("/auth/logout")

    assert _login(client, pending_user.email, TEST_PASSWORD).status_code == 401
    assert _login(client, pending_user.email, NEW_PASSWORD).status_code == 200
    assert client.get("/employees").status_code == 200


def test_the_old_session_stops_working_but_this_device_stays_in(
    client: TestClient, pending_user: User
) -> None:
    _login(client, pending_user.email)
    old_cookie = client.cookies[cookie_name()]

    response = _change(client)

    assert cookie_name() in response.headers["set-cookie"]
    assert client.get("/auth/me").status_code == 200
    # clear() first: otherwise the jar would send both cookies.
    client.cookies.clear()
    client.cookies.set(cookie_name(), old_cookie)
    assert client.get("/auth/me").status_code == 401


def test_the_new_password_is_stored_hashed(
    pending_client: TestClient, pending_user: User
) -> None:
    _change(pending_client)
    assert pending_user.hashed_password != NEW_PASSWORD
    assert verify_password(NEW_PASSWORD, pending_user.hashed_password)


def test_response_exposes_no_credential(pending_client: TestClient) -> None:
    body = _change(pending_client).text
    assert NEW_PASSWORD not in body
    assert "hashed_password" not in body


def test_change_is_audited_without_the_password(
    pending_client: TestClient, pending_user: User, db: Session
) -> None:
    _change(pending_client)

    rows = list(
        db.scalars(select(AuditLog).where(AuditLog.entity_id == pending_user.id))
    )

    assert [r.action for r in rows] == [AuditAction.PASSWORD_CHANGED.value]
    assert rows[0].changes == {
        "must_change_password": {"old": "True", "new": "False"}
    }
    assert NEW_PASSWORD not in str(rows[0].changes)
    assert TEST_PASSWORD not in str(rows[0].changes)


def test_passwords_never_reach_the_logs(
    pending_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        _change(pending_client, current="wrong-guess-value")
        _change(pending_client)

    assert "wrong-guess-value" not in caplog.text
    assert NEW_PASSWORD not in caplog.text
    assert TEST_PASSWORD not in caplog.text


def test_regular_users_can_also_change_their_password(
    auth_client: TestClient, hr_user: User
) -> None:
    assert hr_user.must_change_password is False
    assert _change(auth_client).status_code == 200
    assert auth_client.get("/employees").status_code == 200
