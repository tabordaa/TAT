"""HU-4.6: Colombian holidays are not vacation days."""

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.holidays import holiday_entity_id
from app.core.clock import today
from app.models.audit_log import AuditLog
from app.models.holiday import Holiday
from app.models.user import User, UserRole
from app.services.holidays import colombian_holidays, easter_sunday, next_monday
from app.services.vacations import business_days
from tests.conftest import make_user
from tests.test_vacation_approval import PayloadFactory, _employee_with_account, _login

# The official list for 2026 (decree calendar published by the Ministry of Labor).
OFFICIAL_2026 = [
    date(2026, 1, 1),
    date(2026, 1, 12),
    date(2026, 3, 23),
    date(2026, 4, 2),
    date(2026, 4, 3),
    date(2026, 5, 1),
    date(2026, 5, 18),
    date(2026, 6, 8),
    date(2026, 6, 15),
    date(2026, 6, 29),
    date(2026, 7, 20),
    date(2026, 8, 7),
    date(2026, 8, 17),
    date(2026, 10, 12),
    date(2026, 11, 2),
    date(2026, 11, 16),
    date(2026, 12, 8),
    date(2026, 12, 25),
]


# --- the calculation (CA01) ---------------------------------------------------------


@pytest.mark.parametrize(
    ("year", "expected"),
    [(2024, date(2024, 3, 31)), (2025, date(2025, 4, 20)), (2026, date(2026, 4, 5)),
     (2027, date(2027, 3, 28)), (2038, date(2038, 4, 25))],
)
def test_easter_sunday(year: int, expected: date) -> None:
    assert easter_sunday(year) == expected


def test_the_2026_holidays_match_the_official_list() -> None:
    assert [day for day, _ in colombian_holidays(2026)] == OFFICIAL_2026


@pytest.mark.parametrize("year", range(2024, 2040))
def test_one_entry_per_day_inside_the_year(year: int) -> None:
    days = [day for day, _ in colombian_holidays(year)]
    assert len(days) == len(set(days)) in (17, 18)
    assert all(day.year == year for day in days)


def test_two_holidays_on_the_same_monday_are_one_day_off() -> None:
    # 2025: Sacred Heart (Easter + 68, moved) and Saint Peter (June 29, moved).
    holidays = dict(colombian_holidays(2025))
    assert len(holidays) == 17
    assert holidays[date(2025, 6, 30)] == "San Pedro y San Pablo y Sagrado Corazón de Jesús"


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        (date(2026, 1, 6), date(2026, 1, 12)),  # a Tuesday moves to the next Monday
        (date(2026, 10, 12), date(2026, 10, 12)),  # already a Monday: it stays
        (date(2026, 11, 1), date(2026, 11, 2)),  # a Sunday moves one day
    ],
)
def test_next_monday(day: date, expected: date) -> None:
    assert next_monday(day) == expected


# --- the count (CA02) ---------------------------------------------------------------


@pytest.mark.parametrize(
    ("start", "end", "holidays", "expected"),
    [
        (date(2026, 12, 7), date(2026, 12, 11), {date(2026, 12, 8)}, 4),  # a Tuesday
        (date(2026, 12, 21), date(2027, 1, 8), {date(2026, 12, 25), date(2027, 1, 1)}, 13),
        (date(2026, 11, 16), date(2026, 11, 16), {date(2026, 11, 16)}, 0),  # only a holiday
        (date(2026, 8, 3), date(2026, 8, 9), {date(2026, 8, 8)}, 5),  # a Saturday: no change
        (date(2026, 12, 14), date(2026, 12, 18), {date(2026, 12, 25)}, 5),  # outside the range
    ],
)
def test_business_days_leave_holidays_out(
    start: date, end: date, holidays: set[date], expected: int
) -> None:
    assert business_days(start, end, holidays) == expected


def test_the_seed_holds_the_calculated_holidays(db: Session) -> None:
    stored = set(db.scalars(select(Holiday.day).where(Holiday.day < date(2028, 1, 1))))
    calculated = {day for year in (2026, 2027) for day, _ in colombian_holidays(year)}
    assert calculated <= stored


def _future_week_with_a_weekday_holiday(db: Session) -> tuple[date, date]:
    """The first future Monday whose week has a stored holiday on a weekday."""
    for day in db.scalars(select(Holiday.day).where(Holiday.day > today() + timedelta(days=7))):
        if day.weekday() < 5:
            start = day - timedelta(days=day.weekday())
            return start, start + timedelta(days=4)
    pytest.skip("no stored holiday ahead")


def test_a_request_across_a_holiday_uses_one_day_less(
    client: TestClient,
    db: Session,
    password_hash: str,
    hr_user: User,
    make_employee_payload: PayloadFactory,
) -> None:
    _, user = _employee_with_account(client, make_employee_payload, db, password_hash, hr_user)
    _login(client, user)
    start, end = _future_week_with_a_weekday_holiday(db)

    response = client.post(
        "/me/vacation-requests",
        json={"start_date": start.isoformat(), "end_date": end.isoformat()},
    )

    assert response.status_code == 201, response.text
    assert response.json()["business_days"] == 4


# --- reading and editing the table --------------------------------------------------


def test_anyone_signed_in_reads_the_holidays_of_a_year(
    client: TestClient, db: Session, password_hash: str
) -> None:
    _login(client, make_user(db, password_hash, UserRole.EMPLOYEE))

    response = client.get("/holidays", params={"year": 2026})

    assert response.status_code == 200
    days = [date.fromisoformat(item["day"]) for item in response.json()]
    assert set(OFFICIAL_2026) <= set(days)
    assert days == sorted(days)
    assert {"day": "2026-12-25", "name": "Navidad"} in response.json()


def test_reading_holidays_requires_a_session(client: TestClient) -> None:
    assert client.get("/holidays", params={"year": 2026}).status_code == 401


# A day far from any real holiday, so the test never collides with the seed.
DECREED = date(2099, 9, 17)


def test_an_admin_adds_and_removes_a_holiday(
    client: TestClient, db: Session, password_hash: str
) -> None:
    admin = make_user(db, password_hash, UserRole.ADMIN)
    _login(client, admin)

    added = client.post("/holidays", json={"day": DECREED.isoformat(), "name": "  Día cívico  "})
    assert added.status_code == 201
    assert added.json() == {"day": DECREED.isoformat(), "name": "Día cívico"}
    assert client.post("/holidays", json={"day": DECREED.isoformat(), "name": "Otro"}).status_code == 409

    removed = client.delete(f"/holidays/{DECREED.isoformat()}")
    assert removed.status_code == 204
    assert db.get(Holiday, DECREED) is None
    assert client.delete(f"/holidays/{DECREED.isoformat()}").status_code == 404

    actions = db.scalars(
        select(AuditLog.action)
        .where(AuditLog.entity_id == holiday_entity_id(DECREED), AuditLog.actor_id == admin.id)
        .order_by(AuditLog.created_at)
    ).all()
    assert actions == ["HOLIDAY_ADDED", "HOLIDAY_REMOVED"]


@pytest.mark.parametrize("role", [UserRole.HR, UserRole.MANAGER, UserRole.EMPLOYEE])
def test_only_an_admin_edits_holidays(
    client: TestClient, db: Session, password_hash: str, role: UserRole
) -> None:
    _login(client, make_user(db, password_hash, role))

    assert client.post("/holidays", json={"day": DECREED.isoformat(), "name": "Día"}).status_code == 403
    assert client.delete("/holidays/2026-12-25").status_code == 403


@pytest.mark.parametrize("body", [{"day": "2099-09-17", "name": "x"}, {"day": "no", "name": "Día"},
                                  {"day": "2099-09-17", "name": "Día", "extra": 1}])
def test_an_invalid_holiday_is_422(
    client: TestClient, db: Session, password_hash: str, body: dict[str, object]
) -> None:
    _login(client, make_user(db, password_hash, UserRole.ADMIN))
    assert client.post("/holidays", json=body).status_code == 422


def test_the_entity_id_is_stable() -> None:
    assert holiday_entity_id(DECREED) == holiday_entity_id(date(2099, 9, 17))
    assert isinstance(holiday_entity_id(DECREED), uuid.UUID)
