"""HU-4.4: the absence calendar shows only APPROVED vacations of a month."""

import uuid
from collections.abc import Callable
from datetime import date
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.vacation import VacationRequest, VacationStatus
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]
# A month far in the future: no other test or person has vacations there.
MONTH = "2031-03"


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


@pytest.fixture
def employee(auth_client: TestClient, make_employee_payload: PayloadFactory) -> dict[str, Any]:
    response = auth_client.post("/employees", json=make_employee_payload())
    assert response.status_code == 201
    return response.json()


def _vacation(
    db: Session,
    employee: dict[str, Any],
    by: User,
    start: date,
    end: date,
    status: VacationStatus = VacationStatus.APROBADA,
) -> uuid.UUID:
    vacation = VacationRequest(
        id=uuid.uuid4(),
        employee_id=uuid.UUID(employee["id"]),
        start_date=start,
        end_date=end,
        business_days=1,
        status=status,
        requested_by_id=by.id,
    )
    db.add(vacation)
    db.commit()
    return vacation.id


def _calendar(client: TestClient, month: str = MONTH) -> list[dict[str, Any]]:
    response = client.get("/vacation-calendar", params={"month": month})
    assert response.status_code == 200, response.text
    return response.json()


def test_an_approved_vacation_appears_with_the_employee_name(
    auth_client: TestClient, employee: dict[str, Any], db: Session, hr_user: User
) -> None:
    request_id = _vacation(db, employee, hr_user, date(2031, 3, 10), date(2031, 3, 14))

    absences = _calendar(auth_client)

    assert absences == [
        {
            "request_id": str(request_id),
            "employee_id": employee["id"],
            "employee_name": f"{employee['first_names']} {employee['last_names']}",
            "area": employee["area"],
            "start_date": "2031-03-10",
            "end_date": "2031-03-14",
            "has_photo": False,
        }
    ]


@pytest.mark.parametrize(
    "status", [VacationStatus.PENDIENTE, VacationStatus.RECHAZADA, VacationStatus.CANCELADA]
)
def test_only_approved_vacations_are_shown(
    auth_client: TestClient,
    employee: dict[str, Any],
    db: Session,
    hr_user: User,
    status: VacationStatus,
) -> None:
    _vacation(db, employee, hr_user, date(2031, 3, 10), date(2031, 3, 14), status)
    assert _calendar(auth_client) == []  # CA02


@pytest.mark.parametrize(
    ("start", "end", "shown"),
    [
        (date(2031, 2, 24), date(2031, 3, 4), True),  # starts in the previous month
        (date(2031, 3, 27), date(2031, 4, 4), True),  # ends in the next month
        (date(2031, 2, 20), date(2031, 4, 10), True),  # covers the whole month
        (date(2031, 3, 31), date(2031, 3, 31), True),  # the last day
        (date(2031, 2, 17), date(2031, 2, 28), False),  # ends the day before
        (date(2031, 4, 1), date(2031, 4, 4), False),  # starts the day after
    ],
)
def test_vacations_crossing_the_month_edges(
    auth_client: TestClient,
    employee: dict[str, Any],
    db: Session,
    hr_user: User,
    start: date,
    end: date,
    shown: bool,
) -> None:
    _vacation(db, employee, hr_user, start, end)
    assert (len(_calendar(auth_client)) == 1) is shown


def test_december_ends_on_the_31st(
    auth_client: TestClient, employee: dict[str, Any], db: Session, hr_user: User
) -> None:
    _vacation(db, employee, hr_user, date(2031, 12, 31), date(2032, 1, 2))
    assert len(_calendar(auth_client, "2031-12")) == 1
    assert len(_calendar(auth_client, "2032-01")) == 1


@pytest.mark.parametrize("month", ["2031-13", "2031-3", "31-03", "2031-03-01", "marzo", ""])
def test_the_month_must_be_yyyy_mm(auth_client: TestClient, month: str) -> None:
    response = auth_client.get("/vacation-calendar", params={"month": month})
    assert response.status_code == 422


def test_the_month_is_required(auth_client: TestClient) -> None:
    assert auth_client.get("/vacation-calendar").status_code == 422


@pytest.mark.parametrize(
    ("role", "expected"),
    [(UserRole.ADMIN, 200), (UserRole.HR, 200), (UserRole.MANAGER, 200), (UserRole.EMPLOYEE, 403)],
)
def test_who_reads_the_calendar(
    client: TestClient, db: Session, password_hash: str, role: UserRole, expected: int
) -> None:
    _login(client, make_user(db, password_hash, role))
    response = client.get("/vacation-calendar", params={"month": MONTH})
    assert response.status_code == expected


def test_the_calendar_requires_a_session(client: TestClient) -> None:
    assert client.get("/vacation-calendar", params={"month": MONTH}).status_code == 401
