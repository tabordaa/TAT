"""Create or reset the four accounts the browser tests sign in with.

Usage (from backend/, with the virtual environment active):
    $env:E2E_PASSWORD = "<at least 12 characters>"   # PowerShell
    python -m scripts.e2e_seed

One account per role, each linked to a realistic employee record with a
contract in force. The ``@tat.example.com`` domain is the only thing that marks
them: the script looks them up by email and never touches any other row. The
domain is reserved by RFC 2606, so no mail can ever reach it, and the API's
email validation accepts it (``.test`` is rejected as special-use). Running it
again resets their role, password and access flags, so the tests always start
from the same state.

It refuses to run with ENVIRONMENT=production and prints no password.
"""

import os
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import today
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.employee import (
    ContractType,
    DocumentType,
    Employee,
    EmployeeStatus,
    EmploymentContract,
)
from app.models.user import User, UserRole

MIN_PASSWORD_LENGTH = 12
E2E_DOMAIN = "@tat.example.com"
# A first run on 17 nov 2026 used this domain, which the login rejects. Those
# accounts are renamed instead of left behind (nothing is ever deleted).
_LEGACY_DOMAIN = "@tat.test"


@dataclass(frozen=True)
class Person:
    role: UserRole
    first_names: str
    last_names: str
    email: str
    document_number: str
    position: str
    area: str
    salary: Decimal
    years_of_service: int


# The EMPLOYEE account has exactly one year in its current contract, so it has
# a vacation balance to request against (HU 4.1 and 4.3).
PEOPLE = (
    Person(
        UserRole.ADMIN, "Laura", "Restrepo Gómez", "laura.restrepo@tat.example.com",
        "1036612345", "Administradora de sistemas", "Tecnología", Decimal(9500000), 4,
    ),
    Person(
        UserRole.HR, "Andrés Felipe", "Cardona Ríos", "andres.cardona@tat.example.com",
        "1017234561", "Analista de talento humano", "Talento Humano", Decimal(6200000), 3,
    ),
    Person(
        UserRole.MANAGER, "Catalina", "Mejía Duque", "catalina.mejia@tat.example.com",
        "43987612", "Gerente de operaciones", "Operaciones", Decimal(11000000), 6,
    ),
    Person(
        UserRole.EMPLOYEE, "Juan David", "Ospina Henao", "juan.ospina@tat.example.com",
        "1152698743", "Auxiliar de logística", "Operaciones", Decimal(2600000), 1,
    ),
)


def _active_employee(db: Session, user: User | None, email: str) -> Employee | None:
    """The ACTIVO record already linked to the account, or one with its email."""
    if user is not None and user.employee_id is not None:
        linked = db.get(Employee, user.employee_id)
        if linked is not None and linked.status == EmployeeStatus.ACTIVO:
            return linked
    return db.scalar(
        select(Employee).where(Employee.email == email, Employee.status == EmployeeStatus.ACTIVO)
    )


def _new_employee(db: Session, person: Person, created_by: User) -> Employee:
    start = today() - timedelta(days=365 * person.years_of_service)
    employee = Employee(
        first_names=person.first_names,
        last_names=person.last_names,
        document_type=DocumentType.CC,
        document_number=person.document_number,
        email=person.email,
        position=person.position,
        area=person.area,
        salary=person.salary,
        contract_type=ContractType.INDEFINIDO,
        start_date=start,
        end_date=None,
        created_by_id=created_by.id,
    )
    db.add(employee)
    db.flush()
    db.add(_contract(employee, start, created_by))
    return employee


def _contract(employee: Employee, start: date, created_by: User) -> EmploymentContract:
    return EmploymentContract(
        employee_id=employee.id,
        contract_type=employee.contract_type,
        start_date=start,
        end_date=employee.end_date,
        created_by_id=created_by.id,
    )


def _ensure_contract_in_force(db: Session, employee: Employee, created_by: User) -> None:
    in_force = db.scalar(
        select(EmploymentContract.id).where(
            EmploymentContract.employee_id == employee.id,
            EmploymentContract.terminated_on.is_(None),
        )
    )
    if in_force is None:
        db.add(_contract(employee, employee.start_date, created_by))


def _reset_user(db: Session, person: Person, password_hash: str) -> User:
    user = db.scalar(select(User).where(User.email == person.email))
    if user is None:
        legacy_email = person.email.removesuffix(E2E_DOMAIN) + _LEGACY_DOMAIN
        user = db.scalar(select(User).where(User.email == legacy_email))
    if user is None:
        user = User(email=person.email, hashed_password=password_hash)
        db.add(user)
    user.email = person.email
    user.full_name = f"{person.first_names} {person.last_names}"
    user.role = person.role
    user.hashed_password = password_hash
    user.is_active = True
    user.must_change_password = False
    db.flush()
    return user


def seed(db: Session, password: str, people: tuple[Person, ...] = PEOPLE) -> None:
    """Create or reset ``people``. The first one must be the ADMIN: it is
    recorded as the creator of the employee records."""
    if people[0].role != UserRole.ADMIN:
        raise ValueError("the first person must be the ADMIN")
    password_hash = hash_password(password)  # one hash: Argon2 is slow on purpose
    users = {person.email: _reset_user(db, person, password_hash) for person in people}
    admin = users[people[0].email]

    for person in people:
        user = users[person.email]
        employee = _active_employee(db, user, person.email)
        if employee is None:
            employee = _new_employee(db, person, admin)
        else:
            employee.email = person.email  # only this seed's own linked record
            _ensure_contract_in_force(db, employee, admin)
        user.employee_id = employee.id
    db.commit()


def main() -> int:
    if get_settings().environment == "production":
        print("Refusing to seed test accounts with ENVIRONMENT=production.")
        return 1
    password = os.environ.get("E2E_PASSWORD", "")
    if len(password) < MIN_PASSWORD_LENGTH:
        print(f"Set E2E_PASSWORD (at least {MIN_PASSWORD_LENGTH} characters).")
        return 1
    if not all(person.email.endswith(E2E_DOMAIN) for person in PEOPLE):
        raise AssertionError("every seeded account must use the test domain")

    with SessionLocal() as db:
        seed(db, password)
    for person in PEOPLE:
        print(f"{person.role.value:<8} {person.email}: ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())
