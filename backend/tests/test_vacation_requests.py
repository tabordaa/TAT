"""HU-4.1: an employee requests vacations; every rule is enforced by the server."""

import uuid
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models.audit_log import AuditLog
from app.models.employee import Employee, EmployeeStatus
from app.models.user import User, UserRole
from app.models.vacation import VacationRequest, VacationStatus
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


def monday(weeks_ahead: int = 1) -> date:
    """A Monday in the future, so weekday counts are predictable."""
    now = today()
    return now + timedelta(days=7 - now.weekday() + 7 * (weeks_ahead - 1))


def week(weeks_ahead: int = 1, weeks: int = 1) -> dict[str, str]:
    """Monday to Friday, `weeks` weeks long: 5 business days per week."""
    start = monday(weeks_ahead)
    end = start + timedelta(days=7 * (weeks - 1) + 4)
    return {"start_date": start.isoformat(), "end_date": end.isoformat()}


@pytest.fixture
def employee(
    auth_client: TestClient,
    make_employee_payload: PayloadFactory,
    db: Session,
    password_hash: str,
) -> tuple[dict[str, Any], User]:
    """One year of service (15 days); returns the record and its linked account."""
    created = auth_client.post(
        "/employees",
        json=make_employee_payload(start_date=(today() - timedelta(days=365)).isoformat()),
    )
    assert created.status_code == 201
    record = created.json()
    user = make_user(db, password_hash, UserRole.EMPLOYEE)
    user.employee_id = uuid.UUID(record["id"])
    db.commit()
    return record, user


@pytest.fixture
def as_employee(client: TestClient, employee: tuple[dict[str, Any], User]) -> TestClient:
    _login(client, employee[1])
    return client


# --- the happy path -----------------------------------------------------------------


def test_a_request_stays_pending_with_its_business_days(as_employee: TestClient) -> None:
    response = as_employee.post("/me/vacation-requests", json=week())

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["status"] == "PENDIENTE"  # CA04
    assert body["business_days"] == 5  # CA02: Monday to Friday
    assert body["decided_at"] is None

    balance = as_employee.get("/me/vacation-balance").json()
    assert balance["pending_days"] == 5
    assert balance["available_days"] == "15.00"  # nothing approved yet
    assert balance["requestable_days"] == "10.00"


def test_weekends_inside_the_range_are_not_counted(as_employee: TestClient) -> None:
    start = monday() + timedelta(days=4)  # Friday
    response = as_employee.post(
        "/me/vacation-requests",
        json={"start_date": start.isoformat(), "end_date": (start + timedelta(days=3)).isoformat()},
    )
    assert response.status_code == 201
    assert response.json()["business_days"] == 2  # Friday and Monday


def test_the_request_is_audited(as_employee: TestClient, db: Session) -> None:
    created = as_employee.post("/me/vacation-requests", json=week()).json()

    audit = db.scalars(
        select(AuditLog).where(AuditLog.entity_id == uuid.UUID(created["id"]))
    ).one()
    assert audit.action == "VACATION_REQUESTED"
    assert audit.changes["business_days"] == {"old": None, "new": "5"}
    assert audit.changes["status"] == {"old": None, "new": "PENDIENTE"}


def test_my_requests_are_listed_latest_first(as_employee: TestClient) -> None:
    as_employee.post("/me/vacation-requests", json=week(2))
    as_employee.post("/me/vacation-requests", json=week(4))

    listed = as_employee.get("/me/vacation-requests").json()

    assert [item["start_date"] for item in listed] == [
        week(4)["start_date"],
        week(2)["start_date"],
    ]


def test_others_requests_are_not_listed(
    as_employee: TestClient, db: Session, password_hash: str
) -> None:
    as_employee.post("/me/vacation-requests", json=week())
    other = make_user(db, password_hash, UserRole.HR)  # an account with no record
    _login(as_employee, other)

    assert as_employee.get("/me/vacation-requests").status_code == 404


# --- dates ----------------------------------------------------------------------------


def test_a_range_of_only_weekend_days_is_rejected(as_employee: TestClient) -> None:
    saturday = monday() + timedelta(days=5)
    response = as_employee.post(
        "/me/vacation-requests",
        json={"start_date": saturday.isoformat(), "end_date": (saturday + timedelta(days=1)).isoformat()},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "end_date"


def test_vacations_cannot_start_in_the_past(as_employee: TestClient) -> None:
    yesterday = today() - timedelta(days=1)
    response = as_employee.post(
        "/me/vacation-requests",
        json={"start_date": yesterday.isoformat(), "end_date": (yesterday + timedelta(days=7)).isoformat()},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "start_date"


def test_the_end_cannot_be_before_the_start(as_employee: TestClient) -> None:
    dates = week()
    response = as_employee.post(
        "/me/vacation-requests",
        json={"start_date": dates["end_date"], "end_date": dates["start_date"]},
    )
    assert response.status_code == 422


def test_the_client_cannot_choose_the_status_or_the_days(as_employee: TestClient) -> None:
    response = as_employee.post(
        "/me/vacation-requests", json={**week(), "status": "APROBADA", "business_days": 1}
    )
    assert response.status_code == 422


def test_vacations_cannot_end_after_a_fixed_term_contract(
    client: TestClient,
    auth_client: TestClient,
    make_employee_payload: PayloadFactory,
    db: Session,
    password_hash: str,
) -> None:
    contract_end = monday(2)
    created = auth_client.post(
        "/employees",
        json=make_employee_payload(
            contract_type="FIJO",
            start_date=(today() - timedelta(days=365)).isoformat(),
            end_date=contract_end.isoformat(),
        ),
    ).json()
    user = make_user(db, password_hash, UserRole.EMPLOYEE)
    user.employee_id = uuid.UUID(created["id"])
    db.commit()
    _login(client, user)

    response = client.post("/me/vacation-requests", json=week(2))

    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "end_date"


# --- the balance (CA03) ---------------------------------------------------------------


def test_a_request_above_the_balance_is_rejected(as_employee: TestClient) -> None:
    response = as_employee.post("/me/vacation-requests", json=week(weeks=4))  # 20 > 15

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "business_days"


def test_the_whole_balance_can_be_requested(as_employee: TestClient) -> None:
    response = as_employee.post("/me/vacation-requests", json=week(weeks=3))  # exactly 15
    assert response.status_code == 201


def test_pending_requests_hold_their_days(as_employee: TestClient) -> None:
    assert as_employee.post("/me/vacation-requests", json=week(1, 2)).status_code == 201  # 10

    response = as_employee.post("/me/vacation-requests", json=week(4, 2))  # 10 more > 5 left

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "business_days"


# --- overlaps (decision 7) --------------------------------------------------------------


def test_a_range_overlapping_a_pending_request_is_rejected(as_employee: TestClient) -> None:
    as_employee.post("/me/vacation-requests", json=week())
    wednesday = monday() + timedelta(days=2)

    response = as_employee.post(
        "/me/vacation-requests",
        json={"start_date": wednesday.isoformat(), "end_date": (wednesday + timedelta(days=7)).isoformat()},
    )

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "start_date"


def test_the_next_week_does_not_overlap(as_employee: TestClient) -> None:
    as_employee.post("/me/vacation-requests", json=week(1))
    assert as_employee.post("/me/vacation-requests", json=week(2)).status_code == 201


@pytest.mark.parametrize("status", [VacationStatus.RECHAZADA, VacationStatus.CANCELADA])
def test_a_rejected_or_cancelled_range_can_be_requested_again(
    as_employee: TestClient,
    employee: tuple[dict[str, Any], User],
    db: Session,
    status: VacationStatus,
) -> None:
    record, user = employee
    dates = week()
    db.add(
        VacationRequest(
            employee_id=uuid.UUID(record["id"]),
            start_date=date.fromisoformat(dates["start_date"]),
            end_date=date.fromisoformat(dates["end_date"]),
            business_days=5,
            status=status,
            requested_by_id=user.id,
        )
    )
    db.commit()

    assert as_employee.post("/me/vacation-requests", json=dates).status_code == 201


# --- who can request --------------------------------------------------------------------


def test_an_inactive_employee_cannot_request(
    as_employee: TestClient, employee: tuple[dict[str, Any], User], db: Session
) -> None:
    # Through the API a departure also disables the account (HU-2.7), so this
    # state is set directly: the rule must hold even if an account survives.
    record_row = db.get(Employee, uuid.UUID(employee[0]["id"]))
    assert record_row is not None
    record_row.status = EmployeeStatus.INACTIVO
    db.commit()

    response = as_employee.post("/me/vacation-requests", json=week())

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "status"


def test_an_account_without_a_record_gets_404(
    client: TestClient, db: Session, password_hash: str
) -> None:
    _login(client, make_user(db, password_hash, UserRole.ADMIN))
    assert client.post("/me/vacation-requests", json=week()).status_code == 404


def test_requests_require_a_session(client: TestClient) -> None:
    assert client.post("/me/vacation-requests", json=week()).status_code == 401
    assert client.get("/me/vacation-requests").status_code == 401
