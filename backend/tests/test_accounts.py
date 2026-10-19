"""HU-1.4 Access accounts created together with an employee."""

import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employee import Employee
from app.models.user import User, UserRole
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


@pytest.fixture
def admin_client(client: TestClient, db: Session, password_hash: str) -> TestClient:
    """A client logged in as an ADMIN (the only role allowed to create accounts)."""
    admin = make_user(db, password_hash, UserRole.ADMIN)
    response = client.post(
        "/auth/login", json={"email": admin.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return client


def _count_users(db: Session, email: str) -> int:
    return (
        db.scalar(select(func.count()).select_from(User).where(User.email == email))
        or 0
    )


def _count_employees(db: Session, email: str) -> int:
    return (
        db.scalar(
            select(func.count()).select_from(Employee).where(Employee.email == email)
        )
        or 0
    )


# --- the account is created with the employee --------------------------------


def test_admin_creates_an_employee_with_an_account(
    admin_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload(account_role="MANAGER")

    response = admin_client.post("/employees", json=payload)

    assert response.status_code == 201
    account = response.json()["account"]
    assert account["email"] == payload["email"].lower()
    assert account["role"] == "MANAGER"
    assert account["must_change_password"] is True
    assert len(account["temporary_password"]) >= 12


@pytest.mark.parametrize("role", ["ADMIN", "MANAGER", "HR", "EMPLOYEE"])
def test_every_role_can_be_assigned(
    admin_client: TestClient, make_employee_payload: PayloadFactory, role: str
) -> None:
    response = admin_client.post(
        "/employees", json=make_employee_payload(account_role=role)
    )

    assert response.status_code == 201
    assert response.json()["account"]["role"] == role


def test_the_new_account_is_linked_flagged_and_can_log_in(
    admin_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload(account_role="EMPLOYEE")
    created = admin_client.post("/employees", json=payload).json()
    account = created["account"]

    admin_client.cookies.clear()
    login = admin_client.post(
        "/auth/login",
        json={"email": account["email"], "password": account["temporary_password"]},
    )

    assert login.status_code == 200
    assert login.json()["role"] == "EMPLOYEE"
    assert login.json()["must_change_password"] is True
    assert login.json()["employee_id"] == created["id"]


def test_only_the_hash_of_the_password_is_stored(
    admin_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    account = admin_client.post(
        "/employees", json=make_employee_payload(account_role="HR")
    ).json()["account"]

    user = db.scalar(select(User).where(User.email == account["email"]))

    assert user is not None
    assert user.hashed_password != account["temporary_password"]
    assert account["temporary_password"] not in user.hashed_password
    assert user.hashed_password.startswith("$argon2")


def test_each_account_gets_a_different_password(
    admin_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    first = admin_client.post(
        "/employees", json=make_employee_payload(account_role="HR")
    )
    second = admin_client.post(
        "/employees", json=make_employee_payload(account_role="HR")
    )

    first_password = first.json()["account"]["temporary_password"]
    second_password = second.json()["account"]["temporary_password"]
    assert first_password != second_password


def test_the_response_with_a_password_is_not_cacheable(
    admin_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    response = admin_client.post(
        "/employees", json=make_employee_payload(account_role="HR")
    )

    assert response.headers["cache-control"] == "no-store"


# --- no account unless asked --------------------------------------------------


def test_no_account_is_created_when_no_role_is_given(
    admin_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload()

    response = admin_client.post("/employees", json=payload)

    assert response.status_code == 201
    assert response.json()["account"] is None
    assert _count_users(db, payload["email"].lower()) == 0


# --- who may create accounts --------------------------------------------------


def test_hr_cannot_create_accounts_and_nothing_is_saved(
    auth_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    payload = make_employee_payload(account_role="EMPLOYEE")

    response = auth_client.post("/employees", json=payload)

    assert response.status_code == 403
    assert _count_employees(db, payload["email"].lower()) == 0
    assert _count_users(db, payload["email"].lower()) == 0


def test_hr_can_still_register_employees_without_an_account(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    assert (
        auth_client.post("/employees", json=make_employee_payload()).status_code == 201
    )


# --- validation and atomicity -------------------------------------------------


def test_an_unknown_role_is_rejected(
    admin_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    response = admin_client.post(
        "/employees", json=make_employee_payload(account_role="ROOT")
    )

    assert response.status_code == 422


def test_an_existing_account_email_returns_409_and_saves_nothing(
    admin_client: TestClient,
    db: Session,
    password_hash: str,
    make_employee_payload: PayloadFactory,
) -> None:
    taken = make_user(db, password_hash, UserRole.HR)
    payload = make_employee_payload(email=taken.email, account_role="EMPLOYEE")

    response = admin_client.post("/employees", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "email"
    # All or nothing: the employee must not exist without its account.
    assert _count_employees(db, taken.email) == 0


def test_a_duplicate_employee_does_not_create_an_account(
    admin_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    first = make_employee_payload()
    assert admin_client.post("/employees", json=first).status_code == 201
    duplicate = make_employee_payload(
        document_type=first["document_type"],
        document_number=first["document_number"],
        account_role="HR",
    )

    response = admin_client.post("/employees", json=duplicate)

    assert response.status_code == 409
    assert _count_users(db, duplicate["email"].lower()) == 0


# --- the password never leaks through other endpoints -------------------------


def test_no_other_endpoint_exposes_the_temporary_password(
    admin_client: TestClient, make_employee_payload: PayloadFactory
) -> None:
    created = admin_client.post(
        "/employees", json=make_employee_payload(account_role="HR")
    ).json()
    password = created["account"]["temporary_password"]

    detail = admin_client.get(f"/employees/{created['id']}")
    listing = admin_client.get("/employees", params={"q": created["document_number"]})
    me = admin_client.get("/auth/me")

    for other in (detail, listing, me):
        assert other.status_code == 200
        assert password not in other.text
        assert "hashed_password" not in other.text
        assert "temporary_password" not in other.text


def test_the_new_employee_is_linked_to_exactly_one_account(
    admin_client: TestClient, db: Session, make_employee_payload: PayloadFactory
) -> None:
    created = admin_client.post(
        "/employees", json=make_employee_payload(account_role="HR")
    ).json()

    linked = db.scalars(
        select(User).where(User.employee_id == uuid.UUID(created["id"]))
    ).all()

    assert len(linked) == 1
