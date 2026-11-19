"""HU-4.7: HR sees how many requests wait; an employee sees what was decided."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.vacation import VacationRequest, VacationStatus
from tests.conftest import make_user
from tests.test_vacation_approval import (
    REASON,
    PayloadFactory,
    _employee_with_account,
    _login,
)
from tests.test_vacation_requests import week


@pytest.fixture
def employee(
    client: TestClient,
    make_employee_payload: PayloadFactory,
    db: Session,
    password_hash: str,
    hr_user: User,
) -> User:
    """An EMPLOYEE account with a record and 15 days; the client is logged in as it."""
    _, user = _employee_with_account(client, make_employee_payload, db, password_hash, hr_user)
    _login(client, user)
    return user


def _request(client: TestClient, weeks_ahead: int) -> str:
    response = client.post("/me/vacation-requests", json=week(weeks_ahead))
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def _unseen(client: TestClient) -> dict[str, Any]:
    response = client.get("/me/vacation-requests/unseen")
    assert response.status_code == 200, response.text
    return response.json()


# --- CA01: the pending counter for HR ----------------------------------------------


def test_the_pending_count_follows_the_inbox(
    client: TestClient, employee: User, hr_user: User, db: Session
) -> None:
    first = _request(client, 1)
    _request(client, 2)
    _login(client, hr_user)
    # The database is shared: compare with what it holds, not with a fixed number.
    stored = db.scalar(
        select(func.count())
        .select_from(VacationRequest)
        .where(VacationRequest.status == VacationStatus.PENDIENTE)
    )

    before = client.get("/vacation-requests/pending-count").json()["count"]
    client.post(f"/vacation-requests/{first}/approve")
    after = client.get("/vacation-requests/pending-count").json()["count"]

    assert before == stored
    assert after == before - 1


@pytest.mark.parametrize(
    ("role", "expected"),
    [(UserRole.ADMIN, 200), (UserRole.HR, 200), (UserRole.MANAGER, 403), (UserRole.EMPLOYEE, 403)],
)
def test_only_hr_staff_reads_the_pending_count(
    client: TestClient, db: Session, password_hash: str, role: UserRole, expected: int
) -> None:
    _login(client, make_user(db, password_hash, role))
    assert client.get("/vacation-requests/pending-count").status_code == expected


def test_the_pending_count_requires_a_session(client: TestClient) -> None:
    assert client.get("/vacation-requests/pending-count").status_code == 401


# --- CA02: decisions since my last visit -------------------------------------------


def test_a_decision_by_hr_is_news_until_i_look(
    client: TestClient, employee: User, hr_user: User
) -> None:
    approved = _request(client, 1)
    rejected = _request(client, 2)
    _request(client, 3)  # still pending: not news
    assert _unseen(client)["count"] == 0

    _login(client, hr_user)
    client.post(f"/vacation-requests/{approved}/approve")
    client.post(f"/vacation-requests/{rejected}/reject", json={"reason": REASON})
    _login(client, employee)

    news = _unseen(client)
    assert news["count"] == 2
    assert set(news["request_ids"]) == {approved, rejected}

    assert client.post("/me/vacation-requests/seen").status_code == 204
    assert _unseen(client) == {"count": 0, "request_ids": []}


def test_only_decisions_after_the_visit_are_news(
    client: TestClient, employee: User, hr_user: User
) -> None:
    old = _request(client, 1)
    new = _request(client, 2)
    _login(client, hr_user)
    client.post(f"/vacation-requests/{old}/approve")
    _login(client, employee)
    client.post("/me/vacation-requests/seen")

    _login(client, hr_user)
    client.post(f"/vacation-requests/{new}/approve")
    _login(client, employee)

    assert _unseen(client)["request_ids"] == [new]


def test_my_own_cancellation_is_not_news(client: TestClient, employee: User) -> None:
    mine = _request(client, 1)
    client.post(f"/me/vacation-requests/{mine}/cancel")

    assert _unseen(client)["count"] == 0


def test_a_cancellation_by_a_departure_is_news(
    client: TestClient, employee: User, hr_user: User, db: Session
) -> None:
    mine = _request(client, 1)
    stored = db.get(VacationRequest, uuid.UUID(mine))
    assert stored is not None
    # As the departure does it (cancel_pending_requests), by an HR user.
    stored.status = VacationStatus.CANCELADA
    stored.decided_by_id = hr_user.id
    stored.decided_at = func.now()
    db.commit()

    assert _unseen(client)["request_ids"] == [mine]


def test_someone_elses_decisions_are_not_mine(
    client: TestClient, employee: User, hr_user: User, db: Session, password_hash: str,
    make_employee_payload: PayloadFactory,
) -> None:
    _, other = _employee_with_account(client, make_employee_payload, db, password_hash, hr_user)
    _login(client, other)
    theirs = _request(client, 1)
    _login(client, hr_user)
    client.post(f"/vacation-requests/{theirs}/approve")
    _login(client, employee)

    assert _unseen(client)["count"] == 0


def test_an_account_without_a_record_has_no_vacation_news(
    client: TestClient, db: Session, password_hash: str
) -> None:
    _login(client, make_user(db, password_hash, UserRole.ADMIN))

    assert client.get("/me/vacation-requests/unseen").status_code == 404
    assert client.post("/me/vacation-requests/seen").status_code == 404


def test_vacation_news_requires_a_session(client: TestClient) -> None:
    assert client.get("/me/vacation-requests/unseen").status_code == 401
    assert client.post("/me/vacation-requests/seen").status_code == 401
