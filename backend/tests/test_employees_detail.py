"""HU-2.3 Employee detail (GET /employees/{id})."""

import uuid
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeStatus

PayloadFactory = Callable[..., dict[str, Any]]


def test_detail_returns_the_full_record(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload(phone="3001234567")
    created = auth_client.post("/employees", json=payload).json()

    response = auth_client.get(f"/employees/{created['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == created["id"]
    assert body["first_names"] == payload["first_names"]
    assert body["email"] == payload["email"].lower()
    assert body["phone"] == "3001234567"
    assert body["salary"] == "3500000.00"
    assert body["contract_type"] == "INDEFINIDO"
    assert body["start_date"] == "2026-01-15"
    assert body["status"] == "ACTIVO"


def test_detail_never_exposes_audit_internals(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    created = auth_client.post("/employees", json=make_employee_payload()).json()

    body = auth_client.get(f"/employees/{created['id']}").json()

    assert "created_by_id" not in body
    assert "hashed_password" not in body


def test_detail_shows_inactive_employees_too(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    created = auth_client.post("/employees", json=make_employee_payload()).json()
    employee = db.get(Employee, uuid.UUID(created["id"]))
    assert employee is not None
    employee.status = EmployeeStatus.INACTIVO
    db.commit()  # only releases the SAVEPOINT (see the `db` fixture)

    response = auth_client.get(f"/employees/{created['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVO"


def test_unknown_employee_returns_404_with_a_clear_message(
    auth_client: TestClient,
) -> None:
    response = auth_client.get(f"/employees/{uuid.uuid4()}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Employee not found"


def test_malformed_id_returns_422(auth_client: TestClient) -> None:
    assert auth_client.get("/employees/not-a-uuid").status_code == 422


def test_detail_without_session_returns_401(
    client: TestClient, auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    # `auth_client` and `client` are the same object; log out to drop the session.
    created = auth_client.post("/employees", json=make_employee_payload()).json()
    assert auth_client.post("/auth/logout").status_code == 204

    assert client.get(f"/employees/{created['id']}").status_code == 401


def test_unknown_id_without_session_is_401_not_404(client: TestClient) -> None:
    # Authentication comes first: an anonymous caller must not learn which ids exist.
    assert client.get(f"/employees/{uuid.uuid4()}").status_code == 401
