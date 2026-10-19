"""HU 1.6 Roles and authorization on the real employee endpoints + user-employee link."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]

ALLOWED_ROLES = [UserRole.ADMIN, UserRole.HR]
DENIED_ROLES = [UserRole.MANAGER, UserRole.EMPLOYEE]


def _login_as(
    client: TestClient, db: Session, password_hash: str, role: UserRole
) -> User:
    """Create a user with `role` and log the client in as them (replaces any session)."""
    user = make_user(db, password_hash, role)
    client.cookies.clear()
    response = client.post(
        "/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return user


@pytest.fixture
def employee_id(auth_client: TestClient, make_employee_payload: PayloadFactory) -> str:
    """An employee created by an HR user; the client is left logged in as that HR user."""
    response = auth_client.post("/employees", json=make_employee_payload())
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


# --- no session: 401 ---------------------------------------------------------


def test_employee_endpoints_without_session_return_401(client: TestClient) -> None:
    assert client.get("/employees").status_code == 401
    assert client.get(f"/employees/{uuid.uuid4()}").status_code == 401
    assert client.post("/employees", json={}).status_code == 401


# --- roles with access -------------------------------------------------------


@pytest.mark.parametrize("role", ALLOWED_ROLES)
def test_admin_and_hr_keep_access_to_the_employee_endpoints(
    client: TestClient,
    db: Session,
    password_hash: str,
    make_employee_payload: PayloadFactory,
    role: UserRole,
) -> None:
    _login_as(client, db, password_hash, role)

    created = client.post("/employees", json=make_employee_payload())
    assert created.status_code == 201
    assert client.get("/employees").status_code == 200
    assert client.get(f"/employees/{created.json()['id']}").status_code == 200


# --- roles without access: 403 ----------------------------------------------


@pytest.mark.parametrize("role", DENIED_ROLES)
def test_manager_and_employee_get_403_on_every_employee_endpoint(
    client: TestClient,
    db: Session,
    password_hash: str,
    employee_id: str,
    make_employee_payload: PayloadFactory,
    role: UserRole,
) -> None:
    _login_as(client, db, password_hash, role)

    assert client.get("/employees").status_code == 403
    assert client.get(f"/employees/{employee_id}").status_code == 403
    assert client.post("/employees", json=make_employee_payload()).status_code == 403


def test_403_comes_before_404_and_422(
    client: TestClient, db: Session, password_hash: str
) -> None:
    # A role without permission must not learn whether an id exists or is valid.
    _login_as(client, db, password_hash, UserRole.EMPLOYEE)

    assert client.get(f"/employees/{uuid.uuid4()}").status_code == 403
    assert client.get("/employees/not-a-uuid").status_code in (403, 422)
    assert client.post("/employees", json={}).status_code == 403


# --- every role can log in and see their own session ------------------------


@pytest.mark.parametrize("role", list(UserRole))
def test_every_role_can_log_in_and_read_its_own_session(
    client: TestClient, db: Session, password_hash: str, role: UserRole
) -> None:
    user = _login_as(client, db, password_hash, role)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["role"] == role.value
    assert response.json()["email"] == user.email


def test_the_role_enum_has_the_four_agreed_values() -> None:
    assert {role.value for role in UserRole} == {"ADMIN", "MANAGER", "HR", "EMPLOYEE"}


# --- optional user <-> employee link ----------------------------------------


def test_a_user_without_a_link_reports_a_null_employee_id(
    auth_client: TestClient,
) -> None:
    assert auth_client.get("/auth/me").json()["employee_id"] is None


def test_a_user_can_be_linked_to_an_employee(
    client: TestClient,
    db: Session,
    password_hash: str,
    auth_client: TestClient,
    employee_id: str,
) -> None:
    linked = make_user(db, password_hash, UserRole.EMPLOYEE)
    linked.employee_id = uuid.UUID(employee_id)
    db.commit()  # only releases the SAVEPOINT (see the `db` fixture)
    client.cookies.clear()
    client.post("/auth/login", json={"email": linked.email, "password": TEST_PASSWORD})

    assert client.get("/auth/me").json()["employee_id"] == employee_id


def test_two_accounts_cannot_share_the_same_employee(
    db: Session, password_hash: str, auth_client: TestClient, employee_id: str
) -> None:
    first = make_user(db, password_hash, UserRole.EMPLOYEE)
    second = make_user(db, password_hash, UserRole.EMPLOYEE)
    first.employee_id = uuid.UUID(employee_id)
    db.commit()

    second.employee_id = uuid.UUID(employee_id)
    # begin_nested() keeps the failed statement inside a SAVEPOINT of the test.
    with pytest.raises(IntegrityError), db.begin_nested():
        db.flush()


def test_linking_to_an_unknown_employee_is_rejected(
    db: Session, password_hash: str
) -> None:
    user = make_user(db, password_hash, UserRole.EMPLOYEE)

    user.employee_id = uuid.uuid4()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.flush()
