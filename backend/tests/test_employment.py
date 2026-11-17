"""HU-2.4: PATCH /employees/{id}/employment (position, area, salary)."""

import uuid
from collections.abc import Callable
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.audit_log import AuditAction, AuditLog
from app.models.salary_change import SalaryChange
from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


@pytest.fixture
def employee(auth_client: TestClient, make_employee_payload: PayloadFactory) -> dict[str, Any]:
    """An active employee earning 3,500,000; the client stays logged in as HR."""
    response = auth_client.post("/employees", json=make_employee_payload())
    assert response.status_code == 201
    return response.json()


def _update(client: TestClient, employee_id: str, body: dict[str, Any]):
    return client.patch(f"/employees/{employee_id}/employment", json=body)


def _salary_rows(db: Session, employee_id: str) -> list[SalaryChange]:
    return list(
        db.scalars(
            select(SalaryChange).where(SalaryChange.employee_id == uuid.UUID(employee_id))
        )
    )


def _audit_rows(db: Session, employee_id: str) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog).where(
                AuditLog.entity_id == uuid.UUID(employee_id),
                AuditLog.action == AuditAction.EMPLOYMENT_UPDATED.value,
            )
        )
    )


# --- CA01: the restricted fields can be edited ----------------------------------


def test_hr_promotes_and_raises_an_employee(
    auth_client: TestClient, employee: dict[str, Any], db: Session, hr_user: User
) -> None:
    response = _update(
        auth_client,
        employee["id"],
        {"position": "Coordinadora de nómina", "area": "Talento Humano", "salary": "4200000.50"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["position"] == "Coordinadora de nómina"
    assert body["area"] == "Talento Humano"
    assert Decimal(body["salary"]) == Decimal("4200000.50")  # exact cents, no float
    assert "hashed_password" not in body

    audit = _audit_rows(db, employee["id"])
    assert len(audit) == 1
    assert audit[0].actor_id == hr_user.id
    assert audit[0].changes["salary"] == {"old": "3500000.00", "new": "4200000.50"}
    assert audit[0].changes["position"]["new"] == "Coordinadora de nómina"


def test_an_admin_can_edit_too(
    client: TestClient,
    db: Session,
    password_hash: str,
    employee: dict[str, Any],
) -> None:
    _login(client, make_user(db, password_hash, UserRole.ADMIN))
    assert _update(client, employee["id"], {"position": "Jefe de área"}).status_code == 200


def test_fields_left_out_stay_as_they_are(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    body = _update(auth_client, employee["id"], {"area": "Logística"}).json()

    assert body["area"] == "Logística"
    assert body["position"] == employee["position"]
    assert body["salary"] == employee["salary"]


# --- CA02: the salary history --------------------------------------------------


def test_a_salary_change_writes_one_history_row(
    auth_client: TestClient, employee: dict[str, Any], db: Session, hr_user: User
) -> None:
    _update(auth_client, employee["id"], {"salary": "3800000"})

    rows = _salary_rows(db, employee["id"])
    assert len(rows) == 1
    assert rows[0].old_salary == Decimal("3500000.00")
    assert rows[0].new_salary == Decimal("3800000.00")
    assert rows[0].changed_by_id == hr_user.id
    assert rows[0].changed_at is not None


def test_a_salary_without_cents_is_audited_with_cents(
    auth_client: TestClient, employee: dict[str, Any], db: Session
) -> None:
    _update(auth_client, employee["id"], {"salary": "3800000"})

    change = _audit_rows(db, employee["id"])[0].changes["salary"]
    assert change == {"old": "3500000.00", "new": "3800000.00"}


def test_each_raise_adds_a_row(auth_client: TestClient, employee: dict[str, Any], db: Session) -> None:
    _update(auth_client, employee["id"], {"salary": "3800000"})
    _update(auth_client, employee["id"], {"salary": "4100000"})

    steps = sorted((row.old_salary, row.new_salary) for row in _salary_rows(db, employee["id"]))
    assert steps == [
        (Decimal("3500000.00"), Decimal("3800000.00")),
        (Decimal("3800000.00"), Decimal("4100000.00")),
    ]


def test_changing_only_the_position_writes_no_salary_row(
    auth_client: TestClient, employee: dict[str, Any], db: Session
) -> None:
    _update(auth_client, employee["id"], {"position": "Analista senior"})

    assert _salary_rows(db, employee["id"]) == []
    assert "salary" not in _audit_rows(db, employee["id"])[0].changes


def test_sending_the_same_values_changes_and_logs_nothing(
    auth_client: TestClient, employee: dict[str, Any], db: Session
) -> None:
    response = _update(
        auth_client,
        employee["id"],
        {"salary": "3500000.00", "position": employee["position"]},
    )

    assert response.status_code == 200
    assert _salary_rows(db, employee["id"]) == []
    assert _audit_rows(db, employee["id"]) == []


def test_the_history_table_rejects_a_row_without_a_change(db: Session) -> None:
    check = db.scalar(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE conname = 'ck_salary_changes_differs'"
        )
    )
    assert check is not None and "<>" in check


# --- validation -----------------------------------------------------------------


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"salary": "0"},
        {"salary": "-100"},
        {"salary": "1.234"},
        {"position": ""},
        {"position": "   "},
        {"area": "x" * 121},
        {"status": "INACTIVO"},
        {"first_names": "Otro"},
    ],
)
def test_invalid_bodies_are_rejected(
    auth_client: TestClient, employee: dict[str, Any], body: dict[str, Any]
) -> None:
    assert _update(auth_client, employee["id"], body).status_code == 422


def test_an_inactive_employee_cannot_be_edited(
    auth_client: TestClient, employee: dict[str, Any], db: Session
) -> None:
    terminated = auth_client.post(
        f"/employees/{employee['id']}/contracts/terminate", json={"end_date": "2026-03-01"}
    )
    assert terminated.status_code == 200

    response = _update(auth_client, employee["id"], {"salary": "9000000"})

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "status"
    assert _salary_rows(db, employee["id"]) == []


def test_unknown_employee_is_404(auth_client: TestClient) -> None:
    assert _update(auth_client, str(uuid.uuid4()), {"area": "Ventas"}).status_code == 404


# --- authorization --------------------------------------------------------------


def test_requires_a_session(client: TestClient) -> None:
    assert _update(client, str(uuid.uuid4()), {"area": "Ventas"}).status_code == 401


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.EMPLOYEE])
def test_other_roles_cannot_edit(
    client: TestClient,
    db: Session,
    password_hash: str,
    employee: dict[str, Any],
    role: UserRole,
) -> None:
    _login(client, make_user(db, password_hash, role))

    assert _update(client, employee["id"], {"salary": "9000000"}).status_code == 403
    assert db.scalar(
        select(func.count()).where(SalaryChange.employee_id == uuid.UUID(employee["id"]))
    ) == 0


# --- HU-2.5: GET /employees/{id}/salary-history -------------------------------------


def _history(client: TestClient, employee_id: str):
    return client.get(f"/employees/{employee_id}/salary-history")


def test_history_lists_every_change_newest_first(
    auth_client: TestClient, employee: dict[str, Any], hr_user: User
) -> None:
    _update(auth_client, employee["id"], {"salary": "3800000"})
    _update(auth_client, employee["id"], {"position": "Analista senior"})  # no salary row
    _update(auth_client, employee["id"], {"salary": "4100000.50"})

    response = _history(auth_client, employee["id"])

    assert response.status_code == 200
    rows = response.json()
    assert [(row["old_salary"], row["new_salary"]) for row in rows] == [
        ("3800000.00", "4100000.50"),
        ("3500000.00", "3800000.00"),
    ]
    assert rows[0]["changed_at"] >= rows[1]["changed_at"]
    assert {row["changed_by_name"] for row in rows} == {hr_user.full_name}
    # Only what the history needs: no emails, roles or ids of the account.
    assert set(rows[0]) == {"id", "old_salary", "new_salary", "changed_at", "changed_by_name"}


def test_history_is_empty_before_any_change(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    assert _history(auth_client, employee["id"]).json() == []


def test_history_of_an_unknown_employee_is_404(auth_client: TestClient) -> None:
    assert _history(auth_client, str(uuid.uuid4())).status_code == 404


@pytest.mark.parametrize(
    ("role", "expected"),
    [(UserRole.ADMIN, 200), (UserRole.HR, 200), (UserRole.MANAGER, 200), (UserRole.EMPLOYEE, 403)],
)
def test_history_is_read_by_those_who_read_records(
    client: TestClient,
    db: Session,
    password_hash: str,
    employee: dict[str, Any],
    role: UserRole,
    expected: int,
) -> None:
    _login(client, make_user(db, password_hash, role))
    assert _history(client, employee["id"]).status_code == expected


def test_history_requires_a_session(client: TestClient) -> None:
    assert _history(client, str(uuid.uuid4())).status_code == 401


def test_salary_history_table_has_row_level_security(db: Session) -> None:
    enabled = db.scalar(
        text("SELECT relrowsecurity FROM pg_class WHERE relname = 'salary_changes'")
    )
    assert enabled is True
