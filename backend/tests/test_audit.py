"""HU-5.1 Audit trail: what gets recorded and who can read it."""

import uuid
from collections.abc import Callable
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.core import network
from app.models.audit_log import AuditAction, AuditLog
from app.models.employee import Employee
from app.models.user import User, UserRole
from app.services import audit as audit_service
from app.services.audit import record_audit
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _logged_in(client: TestClient, user: User) -> TestClient:
    response = client.post(
        "/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return client


@pytest.fixture
def admin(db: Session, password_hash: str) -> User:
    return make_user(db, password_hash, UserRole.ADMIN)


@pytest.fixture
def admin_client(client: TestClient, admin: User) -> TestClient:
    return _logged_in(client, admin)


def _rows_for(db: Session, entity_id: uuid.UUID) -> list[AuditLog]:
    return list(db.scalars(select(AuditLog).where(AuditLog.entity_id == entity_id)))


def _fake_request(forwarded: str | None = None) -> Request:
    headers = [(b"x-forwarded-for", forwarded.encode())] if forwarded else []
    return Request({"type": "http", "headers": headers, "client": ("10.0.0.1", 1)})


# --- what is recorded --------------------------------------------------------


def test_creating_an_employee_records_who_what_when_and_ip(
    admin_client: TestClient,
    admin: User,
    db: Session,
    make_employee_payload: PayloadFactory,
) -> None:
    response = admin_client.post(
        "/employees", json=make_employee_payload(salary="4200000.00")
    )
    assert response.status_code == 201

    rows = _rows_for(db, uuid.UUID(response.json()["id"]))

    assert len(rows) == 1
    row = rows[0]
    assert row.action == AuditAction.EMPLOYEE_CREATED.value
    assert row.actor_id == admin.id
    assert row.actor_email == admin.email
    assert row.ip == "testclient"
    assert row.created_at is not None
    assert row.changes["salary"] == {"old": None, "new": "4200000.00"}
    assert row.changes["status"] == {"old": None, "new": "ACTIVO"}


def test_creating_an_account_is_recorded_without_any_credential(
    admin_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload(account_role="EMPLOYEE")
    response = admin_client.post("/employees", json=payload)
    assert response.status_code == 201
    temporary_password = response.json()["account"]["temporary_password"]

    user = db.scalar(select(User).where(User.email == payload["email"].lower()))
    assert user is not None
    rows = _rows_for(db, user.id)

    assert [r.action for r in rows] == [AuditAction.ACCOUNT_CREATED.value]
    assert rows[0].changes["role"]["new"] == "EMPLOYEE"
    stored = str(rows[0].changes)
    assert temporary_password not in stored
    assert user.hashed_password not in stored


def test_rejected_request_leaves_no_audit_row(
    admin_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    before = db.scalar(select(func.count()).select_from(AuditLog))
    response = admin_client.post(
        "/employees", json=make_employee_payload(salary="-1")
    )
    assert response.status_code == 422
    assert db.scalar(select(func.count()).select_from(AuditLog)) == before


def test_change_and_audit_row_share_one_transaction(
    admin_client: TestClient,
    db: Session,
    make_employee_payload: PayloadFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = make_employee_payload()

    def failing_audit(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("audit failed")

    monkeypatch.setattr("app.api.employees.record_audit", failing_audit)

    with pytest.raises(RuntimeError):
        admin_client.post("/employees", json=payload)

    # Same as the request's session being closed without a commit.
    db.rollback()
    created = db.scalar(
        select(func.count())
        .select_from(Employee)
        .where(Employee.email == payload["email"].lower())
    )
    assert created == 0


@pytest.mark.parametrize(
    "field",
    ["password", "temporary_password", "hashed_password", "access_token", "Secret"],
)
def test_secret_fields_are_refused(db: Session, admin: User, field: str) -> None:
    with pytest.raises(ValueError, match="secret"):
        record_audit(
            db,
            actor=admin,
            request=_fake_request(),
            action=AuditAction.PASSWORD_RESET,
            entity_type="user",
            entity_id=admin.id,
            changes={field: ("a", "b")},
        )


def test_recorded_ip_comes_from_the_trusted_proxy_position(
    db: Session, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        network, "get_settings", lambda: SimpleNamespace(trusted_proxy_hops=1)
    )
    record_audit(
        db,
        actor=admin,
        request=_fake_request("6.6.6.6, 200.1.1.1"),
        action=AuditAction.PASSWORD_RESET,
        entity_type="user",
        entity_id=admin.id,
        changes={},
    )
    db.flush()
    assert _rows_for(db, admin.id)[0].ip == "200.1.1.1"


def test_audit_table_has_row_level_security(db: Session) -> None:
    enabled = db.scalar(
        text("SELECT relrowsecurity FROM pg_class WHERE relname = 'audit_logs'")
    )
    assert enabled is True
    assert inspect(db.get_bind()).has_table("audit_logs")


# --- who can read it ---------------------------------------------------------


def test_list_requires_a_session(client: TestClient) -> None:
    assert client.get("/audit").status_code == 401


@pytest.mark.parametrize("role", [UserRole.HR, UserRole.MANAGER, UserRole.EMPLOYEE])
def test_list_is_forbidden_to_other_roles(
    client: TestClient, db: Session, password_hash: str, role: UserRole
) -> None:
    _logged_in(client, make_user(db, password_hash, role))
    assert client.get("/audit").status_code == 403


def test_list_is_newest_first_and_paginated(
    admin_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    ids = [
        admin_client.post("/employees", json=make_employee_payload()).json()["id"]
        for _ in range(3)
    ]
    # now() is frozen inside the test's transaction: set explicit times.
    for offset, employee_id in enumerate(ids):
        db.execute(
            text(
                "UPDATE audit_logs SET created_at = "
                "now() + make_interval(mins => :offset) WHERE entity_id = :id"
            ),
            {"offset": 100 + offset, "id": uuid.UUID(employee_id)},
        )
    db.commit()

    first = admin_client.get("/audit", params={"size": 2}).json()
    second = admin_client.get("/audit", params={"size": 2, "page": 2}).json()

    assert [item["entity_id"] for item in first["items"]] == [ids[2], ids[1]]
    assert second["items"][0]["entity_id"] == ids[0]
    assert first["total"] >= 3
    assert first["page"] == 1
    assert first["size"] == 2


def test_list_exposes_the_who_what_when_and_ip(
    admin_client: TestClient, admin: User, make_employee_payload: PayloadFactory
) -> None:
    created = admin_client.post("/employees", json=make_employee_payload()).json()

    items = admin_client.get("/audit", params={"size": 100}).json()["items"]
    item = next(i for i in items if i["entity_id"] == created["id"])

    assert item["actor_email"] == admin.email
    assert item["action"] == "EMPLOYEE_CREATED"
    assert item["ip"] == "testclient"
    assert item["created_at"]
    assert item["changes"]["status"]["new"] == "ACTIVO"


@pytest.mark.parametrize("params", [{"size": 0}, {"size": 101}, {"page": 0}])
def test_invalid_pagination_is_rejected(
    admin_client: TestClient, params: dict[str, int]
) -> None:
    assert admin_client.get("/audit", params=params).status_code == 422


def test_service_module_never_commits(
    db: Session, admin: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden_commit() -> None:
        raise AssertionError("record_audit must not commit")

    monkeypatch.setattr(db, "commit", forbidden_commit)
    audit_service.record_audit(
        db,
        actor=admin,
        request=_fake_request(),
        action=AuditAction.PASSWORD_RESET,
        entity_type="user",
        entity_id=admin.id,
        changes={},
    )
