"""HU-3.1 Contract assignment and rehire, HU-3.3 Contract termination."""

import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models.audit_log import AuditAction, AuditLog
from app.models.employee import EmploymentContract
from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, cookie_name, make_user

PayloadFactory = Callable[..., dict[str, Any]]

START = "2026-01-15"


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text


def _contract(contract_type: str = "INDEFINIDO", **overrides: Any) -> dict[str, Any]:
    body = {"contract_type": contract_type, "start_date": "2026-06-01", "end_date": None}
    body.update(overrides)
    return body


@pytest.fixture
def employee(auth_client: TestClient, make_employee_payload: PayloadFactory) -> dict[str, Any]:
    """An active employee created by HR; the client stays logged in as HR."""
    response = auth_client.post("/employees", json=make_employee_payload(start_date=START))
    assert response.status_code == 201
    return response.json()


@pytest.fixture
def admin(db: Session, password_hash: str) -> User:
    return make_user(db, password_hash, UserRole.ADMIN)


def _terminate(client: TestClient, employee_id: str, end_date: str = "2026-03-01"):
    return client.post(
        f"/employees/{employee_id}/contracts/terminate", json={"end_date": end_date}
    )


def _assign(client: TestClient, employee_id: str, body: dict[str, Any] | None = None):
    return client.post(f"/employees/{employee_id}/contracts", json=body or _contract())


def _audit_actions(db: Session, employee_id: str) -> list[str]:
    return list(
        db.scalars(
            select(AuditLog.action).where(AuditLog.entity_id == uuid.UUID(employee_id))
        )
    )


# --- HU-3.1 CA01: predefined list ---------------------------------------------


@pytest.mark.parametrize(
    ("contract_type", "end_date"),
    [
        ("INDEFINIDO", None),
        ("FIJO", "2027-06-01"),
        ("OBRA_LABOR", "2027-06-01"),
        ("APRENDIZAJE", "2027-06-01"),
        ("PRESTACION_SERVICIOS", "2027-06-01"),
    ],
)
def test_every_listed_type_can_be_assigned(
    auth_client: TestClient,
    employee: dict[str, Any],
    contract_type: str,
    end_date: str | None,
) -> None:
    response = _assign(
        auth_client, employee["id"], _contract(contract_type, end_date=end_date)
    )
    assert response.status_code == 201
    assert response.json()["contract_type"] == contract_type


def test_a_type_outside_the_list_is_rejected(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    assert _assign(auth_client, employee["id"], _contract("VERBAL")).status_code == 422


def test_registration_also_accepts_the_new_type(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    response = auth_client.post(
        "/employees",
        json=make_employee_payload(
            contract_type="PRESTACION_SERVICIOS", end_date="2027-01-15"
        ),
    )
    assert response.status_code == 201


# --- HU-3.1 CA02 and CA03: the end date depends on the type ---------------------


def test_fixed_term_requires_an_end_date(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    assert _assign(auth_client, employee["id"], _contract("FIJO")).status_code == 422


def test_indefinite_must_not_have_an_end_date(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    body = _contract("INDEFINIDO", end_date="2027-06-01")
    assert _assign(auth_client, employee["id"], body).status_code == 422


def test_registration_applies_the_same_rule(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    response = auth_client.post(
        "/employees", json=make_employee_payload(end_date="2027-01-01")
    )
    assert response.status_code == 422


def test_end_date_cannot_precede_the_start(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    body = _contract("FIJO", end_date="2026-05-31")
    assert _assign(auth_client, employee["id"], body).status_code == 422


def test_status_cannot_be_chosen_by_the_client(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    body = {**_contract(), "status": "INACTIVO"}
    assert _assign(auth_client, employee["id"], body).status_code == 422


# --- assignment over an active contract ------------------------------------------


def test_new_contract_updates_the_record_and_closes_the_old_one(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    body = _contract("FIJO", start_date="2026-06-01", end_date="2027-06-01")

    response = _assign(auth_client, employee["id"], body)

    assert response.json()["contract_type"] == "FIJO"
    assert response.json()["end_date"] == "2027-06-01"
    assert response.json()["status"] == "ACTIVO"
    history = auth_client.get(f"/employees/{employee['id']}/contracts").json()
    assert [c["contract_type"] for c in history] == ["FIJO", "INDEFINIDO"]
    assert history[0]["terminated_on"] is None
    assert history[1]["terminated_on"] == "2026-06-01"


def test_a_contract_cannot_start_before_the_previous_one(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    response = _assign(auth_client, employee["id"], _contract(start_date="2025-01-01"))
    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "start_date"


def test_registration_opens_the_history(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    history = auth_client.get(f"/employees/{employee['id']}/contracts").json()
    assert len(history) == 1
    assert history[0]["start_date"] == START
    assert history[0]["terminated_on"] is None


def test_assignment_is_audited(
    auth_client: TestClient, employee: dict[str, Any], db: Session
) -> None:
    _assign(auth_client, employee["id"], _contract("FIJO", end_date="2027-06-01"))

    row = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(employee["id"]),
            AuditLog.action == AuditAction.CONTRACT_ASSIGNED.value,
        )
    ).one()
    assert row.changes["contract_type"] == {"old": "INDEFINIDO", "new": "FIJO"}


# --- HU-3.1 CA04: rehire --------------------------------------------------------


def test_contract_for_an_inactive_employee_reactivates_them(
    auth_client: TestClient, employee: dict[str, Any], db: Session
) -> None:
    assert _terminate(auth_client, employee["id"]).status_code == 200

    response = _assign(auth_client, employee["id"])

    assert response.status_code == 201
    assert response.json()["status"] == "ACTIVO"
    assert response.json()["start_date"] == "2026-06-01"
    assert AuditAction.EMPLOYEE_REHIRED.value in _audit_actions(db, employee["id"])


def test_rehire_keeps_the_whole_history(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    _terminate(auth_client, employee["id"])
    _assign(auth_client, employee["id"])

    history = auth_client.get(f"/employees/{employee['id']}/contracts").json()

    assert len(history) == 2
    assert history[0]["terminated_on"] is None
    assert history[1]["terminated_on"] == "2026-03-01"


def test_rehire_cannot_start_before_the_departure(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    _terminate(auth_client, employee["id"], "2026-03-01")
    response = _assign(auth_client, employee["id"], _contract(start_date="2026-02-01"))
    assert response.status_code == 409


@pytest.mark.parametrize("field", ["document_number", "email"])
def test_rehire_is_blocked_if_someone_active_took_the_identity(
    auth_client: TestClient,
    employee: dict[str, Any],
    make_employee_payload: PayloadFactory,
    field: str,
) -> None:
    _terminate(auth_client, employee["id"])
    # An inactive record does not block this new registration.
    duplicate = make_employee_payload(
        document_type=employee["document_type"], **{field: employee[field]}
    )
    assert auth_client.post("/employees", json=duplicate).status_code == 201

    response = _assign(auth_client, employee["id"])

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == field


def test_rehire_does_not_reopen_the_account(
    client: TestClient,
    admin: User,
    db: Session,
    make_employee_payload: PayloadFactory,
) -> None:
    _login(client, admin)
    created = client.post(
        "/employees",
        json=make_employee_payload(account_role="EMPLOYEE", start_date=START),
    ).json()
    _terminate(client, created["id"])

    assert _assign(client, created["id"]).status_code == 201

    account = db.scalar(select(User).where(User.employee_id == uuid.UUID(created["id"])))
    assert account is not None
    assert account.is_active is False

    # The administrator's reset is the explicit way back.
    reset = client.post(f"/employees/{created['id']}/account/reset-password")
    assert reset.status_code == 200
    assert account.is_active is True


# --- HU-3.3 CA02: valid departure date ------------------------------------------


def test_end_date_cannot_precede_the_contract_start(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    response = _terminate(auth_client, employee["id"], "2026-01-14")
    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "end_date"


def test_end_date_can_be_the_start_day(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    assert _terminate(auth_client, employee["id"], START).status_code == 200


def test_end_date_cannot_be_in_the_future(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    tomorrow = (today() + timedelta(days=1)).isoformat()
    assert _terminate(auth_client, employee["id"], tomorrow).status_code == 422


def test_malformed_date_is_rejected(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    response = auth_client.post(
        f"/employees/{employee['id']}/contracts/terminate", json={"end_date": "ayer"}
    )
    assert response.status_code == 422


# --- HU-3.3 CA03: inactive, account disabled, data kept -------------------------


def test_termination_changes_the_status_and_keeps_the_record(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    response = _terminate(auth_client, employee["id"])

    assert response.status_code == 200
    assert response.json()["status"] == "INACTIVO"
    assert response.json()["end_date"] == "2026-03-01"
    detail = auth_client.get(f"/employees/{employee['id']}")
    assert detail.status_code == 200
    assert detail.json()["document_number"] == employee["document_number"]


def test_termination_ends_login_and_the_open_session(
    client: TestClient,
    admin: User,
    make_employee_payload: PayloadFactory,
) -> None:
    _login(client, admin)
    created = client.post(
        "/employees", json=make_employee_payload(account_role="HR", start_date=START)
    ).json()
    credentials = {
        "email": created["account"]["email"],
        "password": created["account"]["temporary_password"],
    }
    client.cookies.clear()
    assert client.post("/auth/login", json=credentials).status_code == 200
    open_session = client.cookies[cookie_name()]

    client.cookies.clear()
    _login(client, admin)
    assert _terminate(client, created["id"]).status_code == 200

    client.cookies.clear()
    client.cookies.set(cookie_name(), open_session)
    assert client.get("/auth/me").status_code == 401
    client.cookies.clear()
    assert client.post("/auth/login", json=credentials).status_code == 401


def test_termination_without_an_account_works(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    assert _terminate(auth_client, employee["id"]).status_code == 200


def test_terminating_twice_is_a_conflict(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    _terminate(auth_client, employee["id"])
    response = _terminate(auth_client, employee["id"])
    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "status"


def test_you_cannot_terminate_your_own_contract(
    client: TestClient,
    admin: User,
    db: Session,
    make_employee_payload: PayloadFactory,
) -> None:
    _login(client, admin)
    created = client.post(
        "/employees", json=make_employee_payload(start_date=START)
    ).json()
    admin.employee_id = uuid.UUID(created["id"])
    db.commit()

    assert _terminate(client, created["id"]).status_code == 409


def test_termination_is_audited(
    auth_client: TestClient, employee: dict[str, Any], db: Session
) -> None:
    _terminate(auth_client, employee["id"])

    row = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(employee["id"]),
            AuditLog.action == AuditAction.CONTRACT_TERMINATED.value,
        )
    ).one()
    assert row.changes["status"] == {"old": "ACTIVO", "new": "INACTIVO"}
    assert row.changes["end_date"]["new"] == "2026-03-01"


def test_the_departure_appears_in_the_dashboard(
    auth_client: TestClient, employee: dict[str, Any]
) -> None:
    _terminate(auth_client, employee["id"])
    ids = [
        person["id"]
        for person in auth_client.get("/employees/overview").json()["recent_departures"]
    ]
    assert employee["id"] in ids


# --- authorization --------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/employees/{id}/contracts", "/employees/{id}/contracts/terminate"],
)
def test_writes_require_a_session(client: TestClient, path: str) -> None:
    assert client.post(path.format(id=uuid.uuid4()), json={}).status_code == 401


@pytest.mark.parametrize("role", [UserRole.MANAGER, UserRole.EMPLOYEE])
def test_other_roles_cannot_write(
    client: TestClient,
    db: Session,
    password_hash: str,
    employee: dict[str, Any],
    role: UserRole,
) -> None:
    _login(client, make_user(db, password_hash, role))
    assert _assign(client, employee["id"]).status_code == 403
    assert _terminate(client, employee["id"]).status_code == 403


@pytest.mark.parametrize(
    ("role", "expected"),
    [(UserRole.MANAGER, 200), (UserRole.ADMIN, 200), (UserRole.EMPLOYEE, 403)],
)
def test_history_can_be_read_by_those_who_read_records(
    client: TestClient,
    db: Session,
    password_hash: str,
    employee: dict[str, Any],
    role: UserRole,
    expected: int,
) -> None:
    _login(client, make_user(db, password_hash, role))
    response = client.get(f"/employees/{employee['id']}/contracts")
    assert response.status_code == expected


def test_unknown_employee_is_404(auth_client: TestClient) -> None:
    unknown = uuid.uuid4()
    assert _assign(auth_client, str(unknown)).status_code == 404
    assert _terminate(auth_client, str(unknown)).status_code == 404
    assert auth_client.get(f"/employees/{unknown}/contracts").status_code == 404


# --- the table itself -----------------------------------------------------------


def test_contract_table_has_row_level_security(db: Session) -> None:
    enabled = db.scalar(
        text("SELECT relrowsecurity FROM pg_class WHERE relname = 'employment_contracts'")
    )
    assert enabled is True


def test_each_employee_has_exactly_one_open_contract_after_a_new_assignment(
    auth_client: TestClient, employee: dict[str, Any], db: Session
) -> None:
    _assign(auth_client, employee["id"])
    open_contracts = db.scalar(
        select(func.count())
        .select_from(EmploymentContract)
        .where(
            EmploymentContract.employee_id == uuid.UUID(employee["id"]),
            EmploymentContract.terminated_on.is_(None),
        )
    )
    assert open_contracts == 1
