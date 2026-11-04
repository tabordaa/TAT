"""HU-3.2 Alerts for contracts about to expire (merged with HU-6.2)."""

from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _employee_ending_in(
    client: TestClient, make_payload: PayloadFactory, days: int
) -> dict[str, Any]:
    now = today()
    response = client.post(
        "/employees",
        json=make_payload(
            contract_type="FIJO",
            start_date=(now - timedelta(days=200)).isoformat(),
            end_date=(now + timedelta(days=days)).isoformat(),
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _alert_for(client: TestClient, employee: dict[str, Any]) -> dict[str, Any] | None:
    alerts = client.get("/employees/contract-alerts").json()
    return next((a for a in alerts if a["id"] == employee["id"]), None)


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})


@pytest.mark.parametrize("days", [0, 1, 15, 29])
def test_contracts_ending_in_under_30_days_are_listed(
    auth_client: TestClient, make_employee_payload: PayloadFactory, days: int
) -> None:
    employee = _employee_ending_in(auth_client, make_employee_payload, days)

    alert = _alert_for(auth_client, employee)

    assert alert is not None
    assert alert["days_left"] == days
    assert alert["state"] == "POR_VENCER"
    assert alert["first_names"] == employee["first_names"]


@pytest.mark.parametrize("days", [30, 31, 200])
def test_contracts_ending_later_are_not_listed(
    auth_client: TestClient, make_employee_payload: PayloadFactory, days: int
) -> None:
    employee = _employee_ending_in(auth_client, make_employee_payload, days)
    assert _alert_for(auth_client, employee) is None


def test_expired_contract_of_an_active_employee_stays_listed(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    employee = _employee_ending_in(auth_client, make_employee_payload, -3)

    alert = _alert_for(auth_client, employee)

    assert alert is not None
    assert alert["days_left"] == -3
    assert alert["state"] == "VENCIDO"


def test_inactive_employees_are_excluded(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    employee = _employee_ending_in(auth_client, make_employee_payload, 5)
    assert _alert_for(auth_client, employee) is not None

    terminated = auth_client.post(
        f"/employees/{employee['id']}/contracts/terminate",
        json={"end_date": today().isoformat()},
    )
    assert terminated.status_code == 200

    assert _alert_for(auth_client, employee) is None


def test_indefinite_contracts_are_never_listed(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    created = auth_client.post("/employees", json=make_employee_payload()).json()
    assert _alert_for(auth_client, created) is None


def test_soonest_comes_first(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    later = _employee_ending_in(auth_client, make_employee_payload, 20)
    sooner = _employee_ending_in(auth_client, make_employee_payload, 2)
    expired = _employee_ending_in(auth_client, make_employee_payload, -1)

    ids = [a["id"] for a in auth_client.get("/employees/contract-alerts").json()]

    assert ids.index(expired["id"]) < ids.index(sooner["id"]) < ids.index(later["id"])


def test_alert_exposes_only_what_the_widget_needs(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    employee = _employee_ending_in(auth_client, make_employee_payload, 5)
    alert = _alert_for(auth_client, employee)
    assert alert is not None
    assert set(alert) == {
        "id",
        "first_names",
        "last_names",
        "position",
        "end_date",
        "days_left",
        "state",
    }


def test_the_fixed_path_is_not_read_as_an_employee_id(
    auth_client: TestClient,
) -> None:
    # A plain 200 list proves the route order in main.py: it is not /{employee_id}.
    assert isinstance(auth_client.get("/employees/contract-alerts").json(), list)


def test_requires_a_session(client: TestClient) -> None:
    assert client.get("/employees/contract-alerts").status_code == 401


@pytest.mark.parametrize(
    ("role", "expected"),
    [
        (UserRole.ADMIN, 200),
        (UserRole.HR, 200),
        (UserRole.MANAGER, 200),
        (UserRole.EMPLOYEE, 403),
    ],
)
def test_access_by_role(
    client: TestClient,
    db: Session,
    password_hash: str,
    role: UserRole,
    expected: int,
) -> None:
    _login(client, make_user(db, password_hash, role))
    assert client.get("/employees/contract-alerts").status_code == expected
