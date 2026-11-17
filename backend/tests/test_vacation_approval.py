"""HU-4.2: HR approves or rejects pending vacation requests."""

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
from tests.conftest import TEST_PASSWORD, make_user
from tests.test_vacation_requests import week

PayloadFactory = Callable[..., dict[str, Any]]
REASON = "Cierre contable de fin de mes"


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


def _employee_with_account(
    client: TestClient, payload: PayloadFactory, db: Session, password_hash: str, hr: User
) -> tuple[str, User]:
    """One year of service (15 days) and an EMPLOYEE account linked to it."""
    _login(client, hr)
    created = client.post(
        "/employees",
        json=payload(start_date=(today() - timedelta(days=365)).isoformat()),
    )
    assert created.status_code == 201
    user = make_user(db, password_hash, UserRole.EMPLOYEE)
    user.employee_id = uuid.UUID(created.json()["id"])
    db.commit()
    return created.json()["id"], user


@pytest.fixture
def pending(
    client: TestClient,
    make_employee_payload: PayloadFactory,
    db: Session,
    password_hash: str,
    hr_user: User,
) -> dict[str, Any]:
    """A 5-day PENDIENTE request; the client ends logged in as HR."""
    employee_id, user = _employee_with_account(
        client, make_employee_payload, db, password_hash, hr_user
    )
    _login(client, user)
    created = client.post("/me/vacation-requests", json=week())
    assert created.status_code == 201
    _login(client, hr_user)
    return {**created.json(), "employee_id": employee_id, "user": user}


def _balance(client: TestClient, employee_id: str) -> dict[str, Any]:
    return client.get(f"/employees/{employee_id}/vacation-balance").json()


# --- the inbox (CA01) ---------------------------------------------------------------


def test_the_inbox_lists_pending_requests_with_the_employee(
    client: TestClient, pending: dict[str, Any]
) -> None:
    response = client.get("/vacation-requests")

    assert response.status_code == 200
    item = next(row for row in response.json() if row["id"] == pending["id"])
    assert item["status"] == "PENDIENTE"
    assert item["employee_id"] == pending["employee_id"]
    assert item["employee_name"]  # who asked, not only an id
    assert item["available_days"] == "15.00"
    assert all(row["status"] == "PENDIENTE" for row in response.json())


def test_the_inbox_can_show_other_statuses(client: TestClient, pending: dict[str, Any]) -> None:
    client.post(f"/vacation-requests/{pending['id']}/reject", json={"reason": REASON})

    rejected = client.get("/vacation-requests", params={"status": "RECHAZADA"}).json()
    still_pending = client.get("/vacation-requests").json()

    assert pending["id"] in {row["id"] for row in rejected}
    assert pending["id"] not in {row["id"] for row in still_pending}


@pytest.mark.parametrize(
    ("role", "expected"),
    [(UserRole.ADMIN, 200), (UserRole.HR, 200), (UserRole.MANAGER, 403), (UserRole.EMPLOYEE, 403)],
)
def test_only_hr_staff_reads_the_inbox(
    client: TestClient, db: Session, password_hash: str, role: UserRole, expected: int
) -> None:
    _login(client, make_user(db, password_hash, role))
    assert client.get("/vacation-requests").status_code == expected


def test_the_inbox_requires_a_session(client: TestClient) -> None:
    assert client.get("/vacation-requests").status_code == 401


# --- approve (CA02) -----------------------------------------------------------------


def test_approving_uses_the_days(client: TestClient, pending: dict[str, Any], hr_user: User) -> None:
    response = client.post(f"/vacation-requests/{pending['id']}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == "APROBADA"
    assert response.json()["decided_at"] is not None
    balance = _balance(client, pending["employee_id"])
    assert balance["used_days"] == 5
    assert balance["pending_days"] == 0
    assert balance["available_days"] == "10.00"  # 15 - 5


def test_the_approval_is_audited(client: TestClient, pending: dict[str, Any], db: Session) -> None:
    client.post(f"/vacation-requests/{pending['id']}/approve")

    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(pending["id"]), AuditLog.action == "VACATION_APPROVED"
        )
    ).one()
    assert audit.changes == {"status": {"old": "PENDIENTE", "new": "APROBADA"}}


def test_approval_rechecks_the_balance(
    client: TestClient, pending: dict[str, Any], db: Session
) -> None:
    # Another 12 days were approved meanwhile (e.g. entered by another HR user):
    # 5 more would exceed the 15 earned.
    db.add(
        VacationRequest(
            employee_id=uuid.UUID(pending["employee_id"]),
            start_date=today() + timedelta(days=60),
            end_date=today() + timedelta(days=80),
            business_days=12,
            status=VacationStatus.APROBADA,
            requested_by_id=pending["user"].id,
        )
    )
    db.commit()

    response = client.post(f"/vacation-requests/{pending['id']}/approve")

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "business_days"


# --- reject (CA03) ------------------------------------------------------------------


def test_rejecting_keeps_the_days_and_stores_the_reason(
    client: TestClient, pending: dict[str, Any]
) -> None:
    response = client.post(
        f"/vacation-requests/{pending['id']}/reject", json={"reason": f"  {REASON}  "}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "RECHAZADA"
    assert response.json()["reason"] == REASON  # trimmed
    balance = _balance(client, pending["employee_id"])
    assert balance["used_days"] == 0
    assert balance["pending_days"] == 0
    assert balance["available_days"] == balance["requestable_days"] == "15.00"


@pytest.mark.parametrize("body", [{}, {"reason": ""}, {"reason": "   no "}, {"reason": "x" * 501}])
def test_a_rejection_needs_a_reason(
    client: TestClient, pending: dict[str, Any], body: dict[str, str]
) -> None:
    response = client.post(f"/vacation-requests/{pending['id']}/reject", json=body)
    assert response.status_code == 422


def test_the_employee_sees_the_rejection_reason(
    client: TestClient, pending: dict[str, Any]
) -> None:
    client.post(f"/vacation-requests/{pending['id']}/reject", json={"reason": REASON})
    _login(client, pending["user"])

    mine = client.get("/me/vacation-requests").json()

    assert mine[0]["status"] == "RECHAZADA"
    assert mine[0]["reason"] == REASON


# --- states and permissions -----------------------------------------------------------


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_a_decided_request_cannot_be_decided_again(
    client: TestClient, pending: dict[str, Any], action: str
) -> None:
    assert client.post(f"/vacation-requests/{pending['id']}/approve").status_code == 200

    response = client.post(f"/vacation-requests/{pending['id']}/{action}", json={"reason": REASON})

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "status"


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.EMPLOYEE])
def test_only_hr_staff_decides(
    client: TestClient, pending: dict[str, Any], db: Session, password_hash: str, role: UserRole
) -> None:
    _login(client, make_user(db, password_hash, role))
    assert client.post(f"/vacation-requests/{pending['id']}/approve").status_code == 403


def test_nobody_decides_on_their_own_request(
    client: TestClient, pending: dict[str, Any], db: Session, password_hash: str
) -> None:
    # An HR person who is also the employee who asked.
    hr_employee = make_user(db, password_hash, UserRole.HR)
    owner = db.get(User, pending["user"].id)
    assert owner is not None
    owner.employee_id = None
    db.flush()
    hr_employee.employee_id = uuid.UUID(pending["employee_id"])
    db.commit()
    _login(client, hr_employee)

    response = client.post(f"/vacation-requests/{pending['id']}/approve")

    assert response.status_code == 403


def test_an_unknown_request_is_404(client: TestClient, hr_user: User) -> None:
    _login(client, hr_user)
    assert client.post(f"/vacation-requests/{uuid.uuid4()}/approve").status_code == 404


# --- departure (decision 8) -----------------------------------------------------------


def test_a_departure_cancels_pending_requests(
    client: TestClient, pending: dict[str, Any], db: Session
) -> None:
    terminated = client.post(
        f"/employees/{pending['employee_id']}/contracts/terminate",
        json={"end_date": today().isoformat()},
    )
    assert terminated.status_code == 200

    vacation = db.get(VacationRequest, uuid.UUID(pending["id"]))
    assert vacation is not None
    db.refresh(vacation)
    assert vacation.status is VacationStatus.CANCELADA
    assert vacation.reason == "Contrato finalizado"
    assert vacation.decided_at is not None
    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(pending["employee_id"]),
            AuditLog.action == "CONTRACT_TERMINATED",
        )
    ).one()
    assert audit.changes["pending_vacation_requests"] == {"old": "1", "new": "0"}
    assert pending["id"] not in {row["id"] for row in client.get("/vacation-requests").json()}
