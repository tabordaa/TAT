"""HU-6.1 Dashboard indicators (GET /employees/stats)."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeStatus
from app.models.user import UserRole
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _stats(client: TestClient) -> dict[str, int]:
    response = client.get("/employees/stats")
    assert response.status_code == 200, response.text
    return {key: int(value) for key, value in response.json().items()}


def test_stats_requires_a_session(client: TestClient) -> None:
    assert client.get("/employees/stats").status_code == 401


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.EMPLOYEE])
def test_stats_are_not_available_to_other_roles(
    client: TestClient, db: Session, password_hash: str, role: UserRole
) -> None:
    user = make_user(db, password_hash, role)
    client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})

    assert client.get("/employees/stats").status_code == 403


def test_stats_have_the_three_totals_and_they_add_up(auth_client: TestClient) -> None:
    stats = _stats(auth_client)

    assert set(stats) == {"total", "active", "inactive"}
    assert stats["total"] == stats["active"] + stats["inactive"]


def test_stats_follow_the_database(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    # The database is shared, so compare against a baseline instead of fixed numbers.
    before = _stats(auth_client)
    ids = [
        auth_client.post("/employees", json=make_employee_payload()).json()["id"]
        for _ in range(3)
    ]
    after_hiring = _stats(auth_client)

    employee = db.get(Employee, uuid.UUID(ids[0]))
    assert employee is not None
    employee.status = EmployeeStatus.INACTIVO
    db.commit()  # only releases the SAVEPOINT (see the `db` fixture)
    after_leaving = _stats(auth_client)

    assert after_hiring["total"] == before["total"] + 3
    assert after_hiring["active"] == before["active"] + 3
    assert after_hiring["inactive"] == before["inactive"]
    assert after_leaving["total"] == after_hiring["total"]  # history keeps everyone
    assert after_leaving["active"] == after_hiring["active"] - 1
    assert after_leaving["inactive"] == after_hiring["inactive"] + 1


def test_stats_route_is_not_swallowed_by_the_detail_route(
    auth_client: TestClient,
) -> None:
    # "/employees/stats" must hit the stats handler, not "/employees/{id}" (which would be a 422).
    assert auth_client.get("/employees/stats").status_code == 200
