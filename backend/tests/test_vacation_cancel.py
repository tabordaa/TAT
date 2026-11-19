"""HU-4.5: an employee cancels their own request (PENDING, or APPROVED and not started)."""

import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.models.vacation import VacationRequest, VacationStatus
from tests.conftest import make_user
from tests.test_vacation_approval import _employee_with_account, _login
from tests.test_vacation_requests import week

PayloadFactory = Callable[..., dict[str, Any]]


@pytest.fixture
def mine(
    client: TestClient,
    make_employee_payload: PayloadFactory,
    db: Session,
    password_hash: str,
    hr_user: User,
) -> dict[str, Any]:
    """A 5-day PENDIENTE request; the client ends logged in as its owner."""
    employee_id, user = _employee_with_account(
        client, make_employee_payload, db, password_hash, hr_user
    )
    _login(client, user)
    created = client.post("/me/vacation-requests", json=week())
    assert created.status_code == 201
    return {**created.json(), "employee_id": employee_id, "user": user}


def _cancel(client: TestClient, request_id: str) -> Any:
    return client.post(f"/me/vacation-requests/{request_id}/cancel")


def _balance(client: TestClient) -> dict[str, Any]:
    return client.get("/me/vacation-balance").json()


def test_a_pending_request_is_cancelled_and_frees_the_days(
    client: TestClient, mine: dict[str, Any]
) -> None:
    assert _balance(client)["requestable_days"] == "10.00"  # 15 - 5 pending

    response = _cancel(client, mine["id"])

    assert response.status_code == 200
    assert response.json()["status"] == "CANCELADA"
    assert response.json()["reason"] == "Cancelada por el empleado"
    assert response.json()["decided_at"] is not None
    balance = _balance(client)
    assert balance["pending_days"] == 0
    assert balance["requestable_days"] == "15.00"  # CA02: back at once


def test_an_approved_request_that_has_not_started_can_be_cancelled(
    client: TestClient, mine: dict[str, Any], hr_user: User
) -> None:
    _login(client, hr_user)
    assert client.post(f"/vacation-requests/{mine['id']}/approve").status_code == 200
    _login(client, mine["user"])
    assert _balance(client)["used_days"] == 5

    response = _cancel(client, mine["id"])

    assert response.status_code == 200
    balance = _balance(client)
    assert balance["used_days"] == 0
    assert balance["available_days"] == "15.00"


def _approved_since(db: Session, mine: dict[str, Any], start_offset: int) -> VacationRequest:
    """An APPROVED request starting `start_offset` days from today."""
    vacation = VacationRequest(
        employee_id=uuid.UUID(mine["employee_id"]),
        start_date=today() + timedelta(days=start_offset),
        end_date=today() + timedelta(days=start_offset + 2),
        business_days=1,
        status=VacationStatus.APROBADA,
        requested_by_id=mine["user"].id,
    )
    db.add(vacation)
    db.commit()
    return vacation


@pytest.mark.parametrize("start_offset", [0, -1])
def test_an_approved_request_already_started_cannot_be_cancelled(
    client: TestClient, mine: dict[str, Any], db: Session, start_offset: int
) -> None:
    vacation = _approved_since(db, mine, start_offset)

    response = _cancel(client, str(vacation.id))

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "status"


def test_a_rejected_or_cancelled_request_cannot_be_cancelled(
    client: TestClient, mine: dict[str, Any]
) -> None:
    assert _cancel(client, mine["id"]).status_code == 200

    response = _cancel(client, mine["id"])

    assert response.status_code == 409


def test_someone_elses_request_is_404(
    client: TestClient, mine: dict[str, Any], db: Session, password_hash: str,
    make_employee_payload: PayloadFactory, hr_user: User,
) -> None:
    _, other = _employee_with_account(client, make_employee_payload, db, password_hash, hr_user)
    _login(client, other)

    response = _cancel(client, mine["id"])

    assert response.status_code == 404
    db.expire_all()
    stored = db.get(VacationRequest, uuid.UUID(mine["id"]))
    assert stored is not None and stored.status is VacationStatus.PENDIENTE


def test_an_unknown_request_is_404(client: TestClient, mine: dict[str, Any]) -> None:
    assert _cancel(client, str(uuid.uuid4())).status_code == 404


def test_an_account_without_a_record_is_404(
    client: TestClient, db: Session, password_hash: str
) -> None:
    _login(client, make_user(db, password_hash, UserRole.HR))
    assert _cancel(client, str(uuid.uuid4())).status_code == 404


def test_cancelling_requires_a_session(client: TestClient) -> None:
    assert _cancel(client, str(uuid.uuid4())).status_code == 401


def test_the_cancellation_is_audited(
    client: TestClient, mine: dict[str, Any], db: Session
) -> None:
    _cancel(client, mine["id"])

    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(mine["id"]), AuditLog.action == "VACATION_CANCELLED"
        )
    ).one()
    assert audit.actor_id == mine["user"].id
    assert audit.changes == {"status": {"old": "PENDIENTE", "new": "CANCELADA"}}


def test_a_cancelled_request_leaves_the_inbox(
    client: TestClient, mine: dict[str, Any], hr_user: User
) -> None:
    _cancel(client, mine["id"])
    _login(client, hr_user)

    pending = client.get("/vacation-requests").json()

    assert mine["id"] not in {row["id"] for row in pending}
