"""The browser-test seed (scripts.e2e_seed) is idempotent and only touches its accounts.

These tests seed their OWN people (random suffix), never the real
@tat.example.com accounts, and everything is rolled back by the `db` fixture.
"""

import secrets
from dataclasses import replace
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import verify_password
from app.models.employee import Employee, EmployeeStatus, EmploymentContract
from app.models.user import User, UserRole
from scripts import e2e_seed
from scripts.e2e_seed import Person, seed

PASSWORD = "e2e-seed-test-password"


def _people() -> tuple[Person, ...]:
    suffix = secrets.token_hex(4)
    return tuple(
        Person(
            role,
            "Nombre",
            f"Apellido {suffix}",
            f"{role.value.lower()}.{suffix}@tat-test.example.com",
            f"9{secrets.randbelow(10**9):09d}",
            "Cargo",
            "Área",
            Decimal(3000000),
            years,
        )
        for role, years in (
            (UserRole.ADMIN, 2),
            (UserRole.HR, 2),
            (UserRole.MANAGER, 2),
            (UserRole.EMPLOYEE, 1),
        )
    )


def _user(db: Session, email: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    assert user is not None
    return user


def test_seed_creates_one_linked_account_per_role(db: Session) -> None:
    people = _people()

    seed(db, PASSWORD, people)

    for person in people:
        user = _user(db, person.email)
        assert user.role == person.role
        assert user.is_active and not user.must_change_password
        assert verify_password(PASSWORD, user.hashed_password)
        assert user.employee_id is not None
        employee = db.get(Employee, user.employee_id)
        assert employee is not None and employee.status == EmployeeStatus.ACTIVO
        contracts = db.scalar(
            select(func.count()).where(
                EmploymentContract.employee_id == employee.id,
                EmploymentContract.terminated_on.is_(None),
            )
        )
        assert contracts == 1


def test_seed_twice_resets_without_duplicating(db: Session) -> None:
    people = _people()
    seed(db, PASSWORD, people)
    employee_user = _user(db, people[3].email)
    first_employee_id = employee_user.employee_id
    employee_user.role = UserRole.ADMIN  # a test changed it
    employee_user.must_change_password = True
    db.commit()

    seed(db, "another-password-123", people)

    again = _user(db, people[3].email)
    assert again.role == UserRole.EMPLOYEE
    assert not again.must_change_password
    assert again.employee_id == first_employee_id
    assert verify_password("another-password-123", again.hashed_password)
    employees = db.scalar(select(func.count()).where(Employee.email == people[3].email))
    assert employees == 1


def test_seed_requires_the_admin_first(db: Session) -> None:
    people = _people()
    with pytest.raises(ValueError):
        seed(db, PASSWORD, (people[1], people[0]))


def test_main_refuses_production(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # model_copy skips validation: a production copy without a secure cookie is fine here.
    production = get_settings().model_copy(update={"environment": "production"})
    monkeypatch.setattr(e2e_seed, "get_settings", lambda: production)
    monkeypatch.setenv("E2E_PASSWORD", "long-enough-password")

    assert e2e_seed.main() == 1
    assert "production" in capsys.readouterr().out


def test_main_refuses_a_short_password_without_echoing_it(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("E2E_PASSWORD", "tiny-pw")

    assert e2e_seed.main() == 1
    assert "tiny-pw" not in capsys.readouterr().out


def test_seed_renames_an_account_left_on_the_legacy_domain(db: Session) -> None:
    people = _people()
    local = f"legacy.{secrets.token_hex(4)}"
    admin = replace(people[0], email=f"{local}{e2e_seed.E2E_DOMAIN}")
    legacy = User(
        email=f"{local}@tat.test",
        full_name="Old",
        hashed_password="x",
        role=UserRole.HR,
    )
    db.add(legacy)
    db.flush()

    seed(db, PASSWORD, (admin, *people[1:]))

    renamed = _user(db, admin.email)
    assert renamed.id == legacy.id
    assert renamed.role == UserRole.ADMIN
    assert db.scalar(select(User).where(User.email == f"{local}@tat.test")) is None


def test_real_people_cover_every_role_on_the_test_domain() -> None:
    assert all(person.email.endswith("@tat.example.com") for person in e2e_seed.PEOPLE)
    assert e2e_seed.PEOPLE[0].role == UserRole.ADMIN
    assert {person.role for person in e2e_seed.PEOPLE} == set(UserRole)
