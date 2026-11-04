"""HU-1.5 Manual password reset by an administrator."""

import logging
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.audit_log import AuditAction, AuditLog
from app.models.employee import Employee, EmployeeStatus
from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, cookie_name, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _login(client: TestClient, email: str, password: str = TEST_PASSWORD):
    return client.post("/auth/login", json={"email": email, "password": password})


def _reset_path(employee_id: object) -> str:
    return f"/employees/{employee_id}/account/reset-password"


@pytest.fixture
def admin(db: Session, password_hash: str) -> User:
    return make_user(db, password_hash, UserRole.ADMIN)


@pytest.fixture
def admin_client(client: TestClient, admin: User) -> TestClient:
    assert _login(client, admin.email).status_code == 200
    return client


@pytest.fixture
def target(
    admin_client: TestClient, make_employee_payload: PayloadFactory
) -> dict[str, Any]:
    """An employee with an account, created through the real API."""
    response = admin_client.post(
        "/employees", json=make_employee_payload(account_role="EMPLOYEE")
    )
    assert response.status_code == 201
    return response.json()


def _account(db: Session, target: dict[str, Any]) -> User:
    user = db.scalar(select(User).where(User.employee_id == uuid.UUID(target["id"])))
    assert user is not None
    return user


# --- CA01: only an administrator ---------------------------------------------


def test_requires_a_session(client: TestClient) -> None:
    assert client.post(_reset_path(uuid.uuid4())).status_code == 401


@pytest.mark.parametrize("role", [UserRole.HR, UserRole.MANAGER, UserRole.EMPLOYEE])
def test_other_roles_are_forbidden(
    client: TestClient,
    db: Session,
    password_hash: str,
    role: UserRole,
) -> None:
    other = make_user(db, password_hash, role)
    _login(client, other.email)
    # Forbidden even for an id that does not exist: ids cannot be probed.
    assert client.post(_reset_path(uuid.uuid4())).status_code == 403


def test_detail_tells_whether_the_employee_has_an_account(
    admin_client: TestClient,
    target: dict[str, Any],
    make_employee_payload: PayloadFactory,
) -> None:
    without = admin_client.post("/employees", json=make_employee_payload()).json()

    assert admin_client.get(f"/employees/{target['id']}").json()["has_account"] is True
    assert admin_client.get(f"/employees/{without['id']}").json()["has_account"] is False


# --- CA02: the old password is invalidated, a temporary one is generated -----


def test_reset_returns_a_new_temporary_password(
    admin_client: TestClient, target: dict[str, Any]
) -> None:
    old = target["account"]["temporary_password"]

    response = admin_client.post(_reset_path(target["id"]))

    assert response.status_code == 200
    body = response.json()
    assert body["email"] == target["account"]["email"]
    assert len(body["temporary_password"]) >= 12
    assert body["temporary_password"] != old
    assert response.headers["Cache-Control"] == "no-store"


def test_old_password_stops_working_and_new_one_works(
    admin_client: TestClient, db: Session, target: dict[str, Any]
) -> None:
    old = target["account"]["temporary_password"]
    new = admin_client.post(_reset_path(target["id"])).json()["temporary_password"]

    user = _account(db, target)

    assert not verify_password(old, user.hashed_password)
    assert verify_password(new, user.hashed_password)
    assert new not in user.hashed_password


def test_open_sessions_of_the_account_are_revoked(
    client: TestClient,
    admin: User,
    db: Session,
    target: dict[str, Any],
) -> None:
    client.cookies.clear()
    _login(client, target["account"]["email"], target["account"]["temporary_password"])
    victim_cookie = client.cookies[cookie_name()]
    assert client.get("/auth/me").status_code == 200

    client.cookies.clear()
    _login(client, admin.email)
    assert client.post(_reset_path(target["id"])).status_code == 200

    client.cookies.clear()
    client.cookies.set(cookie_name(), victim_cookie)
    assert client.get("/auth/me").status_code == 401


# --- CA03: back to "requires password change" --------------------------------


def test_reset_turns_the_change_requirement_back_on(
    client: TestClient, admin: User, db: Session, target: dict[str, Any]
) -> None:
    # The employee completes the first change...
    client.cookies.clear()
    _login(client, target["account"]["email"], target["account"]["temporary_password"])
    changed = client.post(
        "/auth/change-password",
        json={
            "current_password": target["account"]["temporary_password"],
            "new_password": "Employee-Chosen-1",
        },
    )
    assert changed.status_code == 200
    assert _account(db, target).must_change_password is False

    # ...the admin resets...
    client.cookies.clear()
    _login(client, admin.email)
    temporary = client.post(_reset_path(target["id"])).json()["temporary_password"]
    assert _account(db, target).must_change_password is True

    # ...and the employee is locked again until a new change.
    client.cookies.clear()
    assert _login(client, target["account"]["email"], temporary).status_code == 200
    assert client.get("/employees").status_code == 403


# --- edge cases ----------------------------------------------------------------


def test_unknown_employee_is_404(admin_client: TestClient) -> None:
    assert admin_client.post(_reset_path(uuid.uuid4())).status_code == 404


def test_employee_without_account_is_404(
    admin_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    created = admin_client.post("/employees", json=make_employee_payload()).json()
    assert admin_client.post(_reset_path(created["id"])).status_code == 404


def test_admin_cannot_reset_their_own_account(
    admin_client: TestClient, admin: User, db: Session, target: dict[str, Any]
) -> None:
    # Link the admin to an employee: only then the panel could reach this account.
    employee_id = uuid.UUID(target["id"])
    target_user = _account(db, target)
    target_user.employee_id = None
    db.flush()
    admin.employee_id = employee_id
    db.commit()

    response = admin_client.post(_reset_path(employee_id))

    assert response.status_code == 409


def test_inactive_employee_cannot_be_given_access(
    admin_client: TestClient, db: Session, target: dict[str, Any]
) -> None:
    employee = db.get(Employee, uuid.UUID(target["id"]))
    assert employee is not None
    employee.status = EmployeeStatus.INACTIVO
    db.commit()

    assert admin_client.post(_reset_path(target["id"])).status_code == 409


def test_reset_reopens_the_account_of_a_rehired_employee(
    admin_client: TestClient, db: Session, target: dict[str, Any]
) -> None:
    user = _account(db, target)
    user.is_active = False
    db.commit()

    assert admin_client.post(_reset_path(target["id"])).status_code == 200

    assert user.is_active is True
    row = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == user.id,
            AuditLog.action == AuditAction.PASSWORD_RESET.value,
        )
    ).one()
    assert row.changes["is_active"] == {"old": "False", "new": "True"}


# --- audit and secrets ---------------------------------------------------------


def test_reset_is_audited_without_any_credential(
    admin_client: TestClient, admin: User, db: Session, target: dict[str, Any]
) -> None:
    temporary = admin_client.post(_reset_path(target["id"])).json()[
        "temporary_password"
    ]
    user = _account(db, target)

    row = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == user.id,
            AuditLog.action == AuditAction.PASSWORD_RESET.value,
        )
    ).one()

    assert row.actor_id == admin.id
    assert temporary not in str(row.changes)
    assert user.hashed_password not in str(row.changes)


def test_temporary_password_never_reaches_the_logs(
    admin_client: TestClient,
    target: dict[str, Any],
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.DEBUG):
        temporary = admin_client.post(_reset_path(target["id"])).json()[
            "temporary_password"
        ]
    assert temporary not in caplog.text
