"""HU-6.1 Dashboard charts and recent movements (GET /employees/overview)."""

import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.employees import OTHERS_LABEL, _group_rest
from app.models.employee import Employee, EmployeeStatus
from app.models.user import UserRole
from app.schemas.employee import CountItem
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _today() -> date:
    # The database compares with its own current_date, which Supabase keeps in UTC.
    return datetime.now(timezone.utc).date()


def _overview(client: TestClient) -> dict[str, Any]:
    response = client.get("/employees/overview")
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def _register(client: TestClient, payload: dict[str, Any]) -> str:
    response = client.post("/employees", json=payload)
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _leave(db: Session, employee_id: str, end_date: date | None = None) -> None:
    employee = db.get(Employee, uuid.UUID(employee_id))
    assert employee is not None
    employee.status = EmployeeStatus.INACTIVO
    employee.end_date = end_date
    db.commit()  # only releases the SAVEPOINT (see the `db` fixture)


def _count_of(items: list[dict[str, Any]], name: str) -> int | None:
    return next((item["count"] for item in items if item["name"] == name), None)


# --- who may see it -----------------------------------------------------------


def test_overview_requires_a_session(client: TestClient) -> None:
    assert client.get("/employees/overview").status_code == 401


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.EMPLOYEE])
def test_overview_is_not_available_to_other_roles(
    client: TestClient, db: Session, password_hash: str, role: UserRole
) -> None:
    user = make_user(db, password_hash, role)
    client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})

    assert client.get("/employees/overview").status_code == 403


def test_overview_route_is_not_swallowed_by_the_detail_route(
    auth_client: TestClient,
) -> None:
    # Otherwise "overview" would be parsed as an employee id and answer 422.
    assert auth_client.get("/employees/overview").status_code == 200


def test_overview_has_the_four_blocks(auth_client: TestClient) -> None:
    assert set(_overview(auth_client)) == {
        "by_area",
        "by_position",
        "recent_hires",
        "recent_departures",
    }


# --- distributions ------------------------------------------------------------


def test_areas_count_only_active_employees(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    area = f"Area-{uuid.uuid4().hex[:8]}"
    ids = [_register(auth_client, make_employee_payload(area=area)) for _ in range(3)]
    assert _count_of(_overview(auth_client)["by_area"], area) == 3

    _leave(db, ids[0])

    assert _count_of(_overview(auth_client)["by_area"], area) == 2


def test_an_area_with_only_inactive_employees_disappears(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    area = f"Area-{uuid.uuid4().hex[:8]}"
    _leave(db, _register(auth_client, make_employee_payload(area=area)))

    assert _count_of(_overview(auth_client)["by_area"], area) is None


def test_areas_are_sorted_from_the_biggest(auth_client: TestClient) -> None:
    counts = [item["count"] for item in _overview(auth_client)["by_area"]]

    assert counts == sorted(counts, reverse=True)


def test_positions_count_only_active_employees(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    # Two employees of the biggest possible group, so the position is never folded away.
    position = f"Cargo-{uuid.uuid4().hex[:8]}"
    ids = [
        _register(auth_client, make_employee_payload(position=position))
        for _ in range(2)
    ]
    _leave(db, ids[0])

    positions = _overview(auth_client)["by_position"]

    assert all(set(item) == {"name", "count"} for item in positions)
    assert all(item["count"] >= 1 for item in positions)


# --- recent movements ---------------------------------------------------------


def test_a_new_hire_appears_first_in_recent_hires(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    employee_id = _register(
        auth_client, make_employee_payload(start_date=_today().isoformat())
    )

    hires = _overview(auth_client)["recent_hires"]

    assert hires[0]["id"] == employee_id
    assert hires[0]["event_date"] == _today().isoformat()


def test_hires_that_have_not_started_yet_are_not_listed(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    tomorrow = _today() + timedelta(days=2)  # +2: safe even across time zones
    employee_id = _register(
        auth_client, make_employee_payload(start_date=tomorrow.isoformat())
    )

    ids = [hire["id"] for hire in _overview(auth_client)["recent_hires"]]

    assert employee_id not in ids


def test_a_departure_appears_in_recent_departures_and_not_in_hires(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    employee_id = _register(
        auth_client,
        make_employee_payload(last_names="Aaaa", start_date=_today().isoformat()),
    )
    _leave(db, employee_id, end_date=_today())

    overview = _overview(auth_client)

    departures = {row["id"]: row for row in overview["recent_departures"]}
    assert departures[employee_id]["event_date"] == _today().isoformat()
    assert employee_id not in [row["id"] for row in overview["recent_hires"]]


def test_active_employees_are_not_listed_as_departures(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    employee_id = _register(auth_client, make_employee_payload())

    ids = [row["id"] for row in _overview(auth_client)["recent_departures"]]

    assert employee_id not in ids


def test_recent_lists_are_capped_and_expose_no_sensitive_data(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    for _ in range(7):
        _register(auth_client, make_employee_payload(start_date=_today().isoformat()))

    hires = _overview(auth_client)["recent_hires"]

    assert len(hires) == 5
    for person in hires:
        assert set(person) == {
            "id",
            "first_names",
            "last_names",
            "position",
            "area",
            "event_date",
        }


# --- grouping of the long tail ------------------------------------------------


def _items(*counts: int) -> list[CountItem]:
    return [CountItem(name=f"P{i}", count=c) for i, c in enumerate(counts)]


def test_few_groups_are_returned_untouched() -> None:
    items = _items(5, 4, 3)

    assert _group_rest(items, limit=3) == items


def test_a_single_left_over_group_keeps_its_own_name() -> None:
    items = _items(5, 4, 3, 2)  # limit 3 leaves only "P3"

    assert _group_rest(items, limit=3) == items


def test_the_tail_is_folded_into_one_bar_with_the_sum() -> None:
    result = _group_rest(_items(9, 8, 7, 3, 2, 1), limit=3)

    assert [(i.name, i.count) for i in result] == [
        ("P0", 9),
        ("P1", 8),
        ("P2", 7),
        (OTHERS_LABEL, 6),
    ]


def test_grouping_never_loses_employees() -> None:
    items = _items(10, 9, 8, 7, 6, 5, 4, 3, 2, 1)

    result = _group_rest(items, limit=6)

    assert sum(i.count for i in result) == sum(i.count for i in items)
    assert len(result) == 7


def test_an_empty_list_stays_empty() -> None:
    assert _group_rest([], limit=6) == []
