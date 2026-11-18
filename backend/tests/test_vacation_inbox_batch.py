"""The inbox's batch balance: same numbers as vacation_balance(), fewer queries."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.clock import today
from app.models.employee import Employee
from app.models.user import User
from app.models.vacation import VacationStatus
from app.services.vacations import available_days_for, vacation_balance
from tests.test_vacation_balance import _add_request, _days_ago

PayloadFactory = Callable[..., dict[str, Any]]


@contextmanager
def count_queries(engine: Engine) -> Iterator[list[str]]:
    """Every SQL statement run on `engine` inside the block."""
    statements: list[str] = []

    def _record(*args: Any) -> None:
        statements.append(args[2])  # (conn, cursor, statement, ...)

    event.listen(engine, "before_cursor_execute", _record)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", _record)


def _create(client: TestClient, payload: PayloadFactory, days_ago: int) -> dict[str, Any]:
    response = client.post("/employees", json=payload(start_date=_days_ago(days_ago)))
    assert response.status_code == 201, response.text
    return response.json()


def _rehired(client: TestClient, payload: PayloadFactory, db: Session, hr: User) -> dict[str, Any]:
    """700 days ago a 10-day approved request on an old contract; rehired 30 days ago."""
    created = _create(client, payload, 800)
    _add_request(
        db, created["id"], hr, VacationStatus.APROBADA, 10, start=today() - timedelta(days=700)
    )
    db.commit()
    terminate = client.post(
        f"/employees/{created['id']}/contracts/terminate", json={"end_date": _days_ago(31)}
    )
    assert terminate.status_code == 200
    rehire = client.post(
        f"/employees/{created['id']}/contracts",
        json={"contract_type": "INDEFINIDO", "start_date": _days_ago(30), "end_date": None},
    )
    assert rehire.status_code == 201
    return created


def _employees(db: Session, created: list[Any]) -> list[Employee]:
    db.expire_all()  # read the status the API just wrote
    return [db.get_one(Employee, item["id"]) for item in created]


def test_the_batch_matches_the_single_balance(
    auth_client: TestClient,
    make_employee_payload: PayloadFactory,
    db: Session,
    hr_user: User,
) -> None:
    with_approved = _create(auth_client, make_employee_payload, 365)
    _add_request(db, with_approved["id"], hr_user, VacationStatus.APROBADA, 5)
    _add_request(db, with_approved["id"], hr_user, VacationStatus.PENDIENTE, 3)  # not "used"
    _add_request(db, with_approved["id"], hr_user, VacationStatus.RECHAZADA, 4)  # never counts
    db.commit()
    untouched = _create(auth_client, make_employee_payload, 100)
    inactive = _create(auth_client, make_employee_payload, 400)
    assert auth_client.post(
        f"/employees/{inactive['id']}/contracts/terminate", json={"end_date": _days_ago(1)}
    ).status_code == 200
    rehired = _rehired(auth_client, make_employee_payload, db, hr_user)

    employees = _employees(db, [with_approved, untouched, inactive, rehired])
    batch = available_days_for(db, employees)

    for employee in employees:
        assert batch[employee.id] == vacation_balance(db, employee).available, (
            f"{employee.first_names}: batch {batch[employee.id]}"
        )


def test_the_batch_does_not_grow_with_the_rows(
    auth_client: TestClient,
    make_employee_payload: PayloadFactory,
    db: Session,
    engine: Engine,
) -> None:
    created = [_create(auth_client, make_employee_payload, 200 + i) for i in range(5)]
    employees = _employees(db, created)

    with count_queries(engine) as one:
        available_days_for(db, employees[:1])
    with count_queries(engine) as five:
        available_days_for(db, employees)

    assert len(five) == len(one), five
    assert len(five) <= 2, five


def test_no_active_employee_means_no_query(db: Session, engine: Engine) -> None:
    with count_queries(engine) as statements:
        assert available_days_for(db, []) == {}
    assert statements == []
