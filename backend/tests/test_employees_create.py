"""HU-2.1 Employee registration (POST /employees)."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.employee import Employee, EmployeeStatus
from app.models.user import User

PayloadFactory = Callable[..., dict[str, Any]]


def _create(client: TestClient, payload: dict[str, Any]):
    return client.post("/employees", json=payload)


def _deactivate(db: Session, employee_id: str) -> None:
    employee = db.get(Employee, uuid.UUID(employee_id))
    assert employee is not None
    employee.status = EmployeeStatus.INACTIVO
    db.commit()  # only releases the SAVEPOINT (see the `db` fixture)


# --- success ---------------------------------------------------------------


def test_create_employee_returns_201_with_server_controlled_fields(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload()

    response = _create(auth_client, payload)

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["first_names"] == payload["first_names"]
    assert body["salary"] == "3500000.00"
    assert body["status"] == "ACTIVO"
    assert body["created_at"]


def test_create_employee_normalizes_document_and_email(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload(
        document_number="ab-123456", email="Mixed.Case@Tat-Test.Example.com"
    )

    body = _create(auth_client, payload).json()

    assert body["document_number"] == "AB-123456"
    assert body["email"] == "mixed.case@tat-test.example.com"


def test_create_employee_records_who_created_it(
    auth_client: TestClient,
    db: Session,
    hr_user: User,
    make_employee_payload: PayloadFactory,
) -> None:
    response = _create(auth_client, make_employee_payload())

    employee = db.get(Employee, uuid.UUID(response.json()["id"]))
    assert employee is not None
    assert employee.created_by_id == hr_user.id


def test_status_cannot_be_chosen_by_the_client(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    # extra="forbid": unknown fields are rejected instead of silently ignored.
    response = _create(auth_client, make_employee_payload(status="INACTIVO"))

    assert response.status_code == 422


# --- duplicates ------------------------------------------------------------


def test_duplicate_document_returns_409_on_document_number(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    first = make_employee_payload()
    assert _create(auth_client, first).status_code == 201

    second = make_employee_payload(
        document_type=first["document_type"], document_number=first["document_number"]
    )
    response = _create(auth_client, second)

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "document_number"


def test_duplicate_document_is_case_insensitive(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    first = make_employee_payload(document_number="ABC12345")
    assert _create(auth_client, first).status_code == 201

    response = _create(auth_client, make_employee_payload(document_number="abc12345"))

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "document_number"


def test_same_number_with_other_document_type_is_allowed(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    first = make_employee_payload(document_type="CC")
    assert _create(auth_client, first).status_code == 201

    other = make_employee_payload(
        document_type="CE", document_number=first["document_number"]
    )

    assert _create(auth_client, other).status_code == 201


def test_duplicate_email_returns_409_on_email(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    first = make_employee_payload()
    assert _create(auth_client, first).status_code == 201

    response = _create(auth_client, make_employee_payload(email=first["email"].upper()))

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "email"


def test_rehire_after_inactive_is_allowed(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    # The unique indexes are PARTIAL (only ACTIVO), so an INACTIVO record
    # must not block the same person from being registered again.
    first = make_employee_payload()
    created = _create(auth_client, first)
    assert created.status_code == 201
    _deactivate(db, created.json()["id"])

    rehire = make_employee_payload(
        document_type=first["document_type"],
        document_number=first["document_number"],
        email=first["email"],
    )
    response = _create(auth_client, rehire)

    assert response.status_code == 201
    assert response.json()["id"] != created.json()["id"]


# --- validation ------------------------------------------------------------


@pytest.mark.parametrize("field", ["email", "area", "salary"])
def test_missing_required_field_returns_422(
    auth_client: TestClient, make_employee_payload: PayloadFactory, field: str
) -> None:
    payload = make_employee_payload()
    del payload[field]

    response = _create(auth_client, payload)

    assert response.status_code == 422
    assert any(error["loc"][-1] == field for error in response.json()["detail"])


@pytest.mark.parametrize("salary", ["0", "-1", "-3500000.00"])
def test_non_positive_salary_returns_422(
    auth_client: TestClient, make_employee_payload: PayloadFactory, salary: str
) -> None:
    assert _create(auth_client, make_employee_payload(salary=salary)).status_code == 422


def test_salary_with_more_than_two_decimals_returns_422(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    assert (
        _create(auth_client, make_employee_payload(salary="100.123")).status_code == 422
    )


def test_invalid_email_returns_422(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    assert (
        _create(auth_client, make_employee_payload(email="not-an-email")).status_code
        == 422
    )


@pytest.mark.parametrize(
    "document_number", ["123", "has space1", "x" * 21, "bad_char#1"]
)
def test_invalid_document_number_returns_422(
    auth_client: TestClient, make_employee_payload: PayloadFactory, document_number: str
) -> None:
    response = _create(
        auth_client, make_employee_payload(document_number=document_number)
    )

    assert response.status_code == 422


def test_fixed_term_contract_requires_end_date(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    response = _create(
        auth_client, make_employee_payload(contract_type="FIJO", end_date=None)
    )

    assert response.status_code == 422


def test_end_date_cannot_be_before_start_date(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload(
        contract_type="FIJO", start_date="2026-06-01", end_date="2026-05-31"
    )

    assert _create(auth_client, payload).status_code == 422


def test_fixed_term_contract_with_valid_dates_is_created(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload(
        contract_type="FIJO", start_date="2026-06-01", end_date="2027-05-31"
    )

    response = _create(auth_client, payload)

    assert response.status_code == 201
    assert response.json()["end_date"] == "2027-05-31"


# --- authentication --------------------------------------------------------


def test_create_employee_without_session_returns_401(
    client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    assert _create(client, make_employee_payload()).status_code == 401
