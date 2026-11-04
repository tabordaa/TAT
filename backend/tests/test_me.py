"""HU-2.6 My profile: an employee sees only their own record."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text


@pytest.fixture
def two_employees(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> list[dict[str, Any]]:
    """Two records created by HR; the client stays logged in as HR."""
    return [
        auth_client.post(
            "/employees", json=make_employee_payload(first_names=name)
        ).json()
        for name in ("Propia", "Ajena")
    ]


def _linked_user(
    db: Session, password_hash: str, employee: dict[str, Any], role: UserRole
) -> User:
    user = make_user(db, password_hash, role)
    user.employee_id = uuid.UUID(employee["id"])
    db.commit()
    return user


def test_requires_a_session(client: TestClient) -> None:
    assert client.get("/me/employee").status_code == 401


def test_employee_sees_their_own_record(
    client: TestClient,
    db: Session,
    password_hash: str,
    two_employees: list[dict[str, Any]],
) -> None:
    own = two_employees[0]
    _login(client, _linked_user(db, password_hash, own, UserRole.EMPLOYEE))

    response = client.get("/me/employee")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == own["id"]
    assert body["first_names"] == "Propia"
    assert body["salary"] == own["salary"]  # CA: validate their labor conditions


def test_employee_cannot_read_a_colleague(
    client: TestClient,
    db: Session,
    password_hash: str,
    two_employees: list[dict[str, Any]],
) -> None:
    own, other = two_employees
    _login(client, _linked_user(db, password_hash, own, UserRole.EMPLOYEE))

    assert client.get(f"/employees/{other['id']}").status_code == 403
    assert client.get(f"/employees/{own['id']}").status_code == 403
    assert client.get("/me/employee", params={"id": other["id"]}).json()["id"] == own["id"]


def test_employee_cannot_see_the_directory_or_change_labor_data(
    client: TestClient,
    db: Session,
    password_hash: str,
    two_employees: list[dict[str, Any]],
    make_employee_payload: PayloadFactory,
) -> None:
    _login(
        client, _linked_user(db, password_hash, two_employees[0], UserRole.EMPLOYEE)
    )

    assert client.get("/employees").status_code == 403
    assert client.post("/employees", json=make_employee_payload()).status_code == 403


def test_account_without_a_record_gets_404(
    client: TestClient, db: Session, password_hash: str
) -> None:
    _login(client, make_user(db, password_hash, UserRole.EMPLOYEE))
    assert client.get("/me/employee").status_code == 404


def test_response_exposes_no_account_secret(
    client: TestClient,
    db: Session,
    password_hash: str,
    two_employees: list[dict[str, Any]],
) -> None:
    _login(
        client, _linked_user(db, password_hash, two_employees[0], UserRole.EMPLOYEE)
    )
    assert "hashed_password" not in client.get("/me/employee").text


def test_temporary_password_cannot_open_the_profile(
    client: TestClient,
    db: Session,
    password_hash: str,
    two_employees: list[dict[str, Any]],
) -> None:
    user = _linked_user(db, password_hash, two_employees[0], UserRole.EMPLOYEE)
    user.must_change_password = True
    db.commit()
    _login(client, user)

    assert client.get("/me/employee").status_code == 403


@pytest.mark.parametrize("role", list(UserRole))
def test_any_role_linked_to_a_record_can_open_it(
    client: TestClient,
    db: Session,
    password_hash: str,
    two_employees: list[dict[str, Any]],
    role: UserRole,
) -> None:
    _login(client, _linked_user(db, password_hash, two_employees[0], role))
    assert client.get("/me/employee").status_code == 200
