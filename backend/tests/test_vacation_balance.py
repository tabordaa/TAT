"""HU-4.3: vacation balance, calculated on every read from the contract in force."""

import uuid
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models.user import User, UserRole
from app.models.vacation import VacationRequest, VacationStatus
from app.services.vacations import accrued_days, business_days
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


def _days_ago(days: int) -> str:
    return (today() - timedelta(days=days)).isoformat()


@pytest.fixture
def employee(auth_client: TestClient, make_employee_payload: PayloadFactory) -> dict[str, Any]:
    """Exactly one year in the contract in force; the client stays logged in as HR."""
    response = auth_client.post("/employees", json=make_employee_payload(start_date=_days_ago(365)))
    assert response.status_code == 201
    return response.json()


def _add_request(
    db: Session,
    employee_id: str,
    requested_by: User,
    status: VacationStatus,
    days: int,
    start: date | None = None,
) -> None:
    start = start or today() + timedelta(days=30)
    db.add(
        VacationRequest(
            employee_id=uuid.UUID(employee_id),
            start_date=start,
            end_date=start + timedelta(days=days + 2),  # dates only matter for the contract filter
            business_days=days,
            status=status,
            requested_by_id=requested_by.id,
        )
    )
    db.flush()


def _balance(client: TestClient, employee_id: str) -> dict[str, Any]:
    response = client.get(f"/employees/{employee_id}/vacation-balance")
    assert response.status_code == 200, response.text
    return response.json()


# --- the calculation -------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end", "expected"),
    [
        (date(2026, 11, 16), date(2026, 11, 20), 5),  # Monday to Friday
        (date(2026, 11, 21), date(2026, 11, 22), 0),  # a weekend
        (date(2026, 11, 20), date(2026, 11, 23), 2),  # Friday to Monday
        (date(2026, 11, 18), date(2026, 11, 18), 1),  # one Wednesday
        (date(2026, 11, 2), date(2026, 11, 15), 10),  # two full weeks
        (date(2026, 12, 21), date(2027, 1, 8), 15),  # across the new year, holidays count
        (date(2026, 11, 20), date(2026, 11, 19), 0),  # end before start
    ],
)
def test_business_days_leave_out_only_weekends(start: date, end: date, expected: int) -> None:
    assert business_days(start, end) == expected


@pytest.mark.parametrize(
    ("days_worked", "expected"),
    [
        (365, Decimal("15.00")),  # CA01: 15 days per year worked
        (730, Decimal("30.00")),
        (100, Decimal("4.10")),  # 4.109... rounded DOWN: not earned yet
        (1, Decimal("0.04")),
        (0, Decimal("0.00")),
        (-10, Decimal("0.00")),  # a contract that starts in the future
    ],
)
def test_accrued_days_are_proportional(days_worked: int, expected: Decimal) -> None:
    on = date(2026, 11, 17)
    assert accrued_days(on - timedelta(days=days_worked), on) == expected


# --- the balance through the API -----------------------------------------------


def test_one_year_of_service_gives_fifteen_days(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    balance = _balance(auth_client, employee["id"])

    assert balance == {
        "days_per_year": 15,
        "contract_start": employee["start_date"],
        "accrued_days": "15.00",
        "used_days": 0,
        "pending_days": 0,
        "available_days": "15.00",
        "requestable_days": "15.00",
    }


def test_only_approved_requests_are_subtracted(
    auth_client: TestClient, employee: dict[str, Any], db: Session, hr_user: User
) -> None:
    _add_request(db, employee["id"], hr_user, VacationStatus.APROBADA, 5)
    _add_request(db, employee["id"], hr_user, VacationStatus.APROBADA, 2)
    _add_request(db, employee["id"], hr_user, VacationStatus.PENDIENTE, 3)
    _add_request(db, employee["id"], hr_user, VacationStatus.RECHAZADA, 4)
    _add_request(db, employee["id"], hr_user, VacationStatus.CANCELADA, 6)

    balance = _balance(auth_client, employee["id"])

    # CA02: 15 - (5 + 2); rejected and cancelled requests change nothing.
    assert balance["used_days"] == 7
    assert balance["available_days"] == "8.00"
    # Decision 3: what can still be requested also discounts the pending ones.
    assert balance["pending_days"] == 3
    assert balance["requestable_days"] == "5.00"


def test_a_rehire_starts_from_zero(
    auth_client: TestClient,
    make_employee_payload: PayloadFactory,
    db: Session,
    hr_user: User,
) -> None:
    created = auth_client.post(
        "/employees", json=make_employee_payload(start_date=_days_ago(800))
    ).json()
    old_start = today() - timedelta(days=700)
    _add_request(db, created["id"], hr_user, VacationStatus.APROBADA, 10, start=old_start)
    db.commit()
    assert auth_client.post(
        f"/employees/{created['id']}/contracts/terminate", json={"end_date": _days_ago(31)}
    ).status_code == 200
    assert auth_client.post(
        f"/employees/{created['id']}/contracts",
        json={"contract_type": "INDEFINIDO", "start_date": _days_ago(30), "end_date": None},
    ).status_code == 200

    balance = _balance(auth_client, created["id"])

    # Decision 5: only the contract in force; the old request does not count.
    assert balance["contract_start"] == _days_ago(30)
    assert balance["accrued_days"] == "1.23"  # 15 x 30 / 365, rounded down
    assert balance["used_days"] == 0


def test_an_inactive_employee_has_no_balance(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    terminated = auth_client.post(
        f"/employees/{employee['id']}/contracts/terminate", json={"end_date": _days_ago(1)}
    )
    assert terminated.status_code == 200

    balance = _balance(auth_client, employee["id"])

    assert balance["contract_start"] is None
    assert balance["accrued_days"] == balance["available_days"] == "0.00"


def test_the_balance_is_never_stored(db: Session) -> None:
    columns = db.scalars(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name IN ('employees', 'employment_contracts', 'vacation_requests')"
        )
    ).all()
    assert not any("balance" in column or "accrued" in column for column in columns)


# --- my own balance ------------------------------------------------------------


def test_an_employee_reads_their_own_balance(
    client: TestClient,
    db: Session,
    password_hash: str,
    employee: dict[str, Any],
) -> None:
    user = make_user(db, password_hash, UserRole.EMPLOYEE)
    user.employee_id = uuid.UUID(employee["id"])
    db.commit()
    _login(client, user)

    response = client.get("/me/vacation-balance")

    assert response.status_code == 200
    assert response.json()["accrued_days"] == "15.00"


def test_an_account_without_a_record_gets_404(
    client: TestClient, db: Session, password_hash: str
) -> None:
    _login(client, make_user(db, password_hash, UserRole.ADMIN))
    assert client.get("/me/vacation-balance").status_code == 404


def test_my_balance_requires_a_session(client: TestClient) -> None:
    assert client.get("/me/vacation-balance").status_code == 401


# --- authorization --------------------------------------------------------------


@pytest.mark.parametrize(
    ("role", "expected"),
    [(UserRole.ADMIN, 200), (UserRole.HR, 200), (UserRole.MANAGER, 200), (UserRole.EMPLOYEE, 403)],
)
def test_others_balance_is_read_by_those_who_read_records(
    client: TestClient,
    db: Session,
    password_hash: str,
    employee: dict[str, Any],
    role: UserRole,
    expected: int,
) -> None:
    _login(client, make_user(db, password_hash, role))
    response = client.get(f"/employees/{employee['id']}/vacation-balance")
    assert response.status_code == expected


def test_unknown_employee_is_404(auth_client: TestClient) -> None:
    response = auth_client.get(f"/employees/{uuid.uuid4()}/vacation-balance")
    assert response.status_code == 404


def test_vacation_table_has_row_level_security(db: Session) -> None:
    enabled = db.scalar(
        text("SELECT relrowsecurity FROM pg_class WHERE relname = 'vacation_requests'")
    )
    assert enabled is True
