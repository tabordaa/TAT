"""HU-4.8: the absence calendar filtered by area, and the list of areas."""

import uuid
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models.user import User, UserRole
from tests.conftest import make_user
from tests.test_vacation_calendar import MONTH, PayloadFactory, _login, _vacation


def _in_area(client: TestClient, payload: PayloadFactory, area: str) -> dict[str, Any]:
    response = client.post("/employees", json=payload(area=area))
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def two_areas(
    auth_client: TestClient, make_employee_payload: PayloadFactory, db: Session, hr_user: User
) -> tuple[str, str, dict[str, Any], dict[str, Any]]:
    """Two areas unique to this test, each with one approved absence in MONTH."""
    suffix = uuid.uuid4().hex[:8]
    sales, legal = f"Ventas {suffix}", f"Jurídica {suffix}"
    seller = _in_area(auth_client, make_employee_payload, sales)
    lawyer = _in_area(auth_client, make_employee_payload, legal)
    _vacation(db, seller, hr_user, date(2031, 3, 10), date(2031, 3, 12))
    _vacation(db, lawyer, hr_user, date(2031, 3, 11), date(2031, 3, 13))
    return sales, legal, seller, lawyer


def test_the_calendar_keeps_only_the_area_asked_for(
    auth_client: TestClient, two_areas: tuple[str, str, dict[str, Any], dict[str, Any]]
) -> None:
    sales, _, seller, lawyer = two_areas

    response = auth_client.get("/vacation-calendar", params={"month": MONTH, "area": sales})

    assert response.status_code == 200
    ids = {row["employee_id"] for row in response.json()}
    assert seller["id"] in ids
    assert lawyer["id"] not in ids
    assert all(row["area"] == sales for row in response.json())


def test_without_an_area_everybody_is_shown(
    auth_client: TestClient, two_areas: tuple[str, str, dict[str, Any], dict[str, Any]]
) -> None:
    _, legal, seller, lawyer = two_areas

    rows = auth_client.get("/vacation-calendar", params={"month": MONTH}).json()

    assert {seller["id"], lawyer["id"]} <= {row["employee_id"] for row in rows}
    assert next(row for row in rows if row["employee_id"] == lawyer["id"])["area"] == legal


def test_an_unknown_area_is_an_empty_month(auth_client: TestClient) -> None:
    response = auth_client.get(
        "/vacation-calendar", params={"month": MONTH, "area": f"Nadie {uuid.uuid4().hex}"}
    )
    assert response.status_code == 200
    assert response.json() == []


def test_the_areas_of_active_employees_are_listed_once(
    auth_client: TestClient, two_areas: tuple[str, str, dict[str, Any], dict[str, Any]],
    make_employee_payload: PayloadFactory,
) -> None:
    sales, legal, _, _ = two_areas
    _in_area(auth_client, make_employee_payload, sales)  # a second person in the same area

    areas = auth_client.get("/employees/areas").json()

    assert areas.count(sales) == 1
    assert legal in areas
    assert areas == sorted(areas)


def test_an_area_with_only_inactive_people_is_not_offered(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    gone = f"Cerrada {uuid.uuid4().hex[:8]}"
    person = _in_area(auth_client, make_employee_payload, gone)
    terminated = auth_client.post(
        f"/employees/{person['id']}/contracts/terminate",
        json={"end_date": today().isoformat()},
    )
    assert terminated.status_code == 200

    assert gone not in auth_client.get("/employees/areas").json()


@pytest.mark.parametrize(
    ("role", "expected"),
    [(UserRole.ADMIN, 200), (UserRole.HR, 200), (UserRole.MANAGER, 200), (UserRole.EMPLOYEE, 403)],
)
def test_who_reads_the_areas(
    client: TestClient, db: Session, password_hash: str, role: UserRole, expected: int
) -> None:
    _login(client, make_user(db, password_hash, role))
    assert client.get("/employees/areas").status_code == expected
