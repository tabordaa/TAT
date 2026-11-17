"""HU-5.2: the employee list as CSV, with the screen's filters."""

import csv
import io
import uuid
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api import employees as employees_api
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.services.employee_export import BOM, neutralize
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post("/auth/login", json={"email": user.email, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


def _rows(response: Any) -> list[list[str]]:
    text = response.content.decode("utf-8")
    assert text.startswith(BOM)  # Excel needs it to read tildes and the ñ
    return list(csv.reader(io.StringIO(text[len(BOM) :]), delimiter=";"))


@pytest.fixture
def tag() -> str:
    """A unique word in the last names, so the filter finds only this test's people."""
    return f"Zexport{uuid.uuid4().hex[:8]}"


@pytest.fixture
def people(
    auth_client: TestClient, make_employee_payload: PayloadFactory, tag: str
) -> list[dict[str, Any]]:
    """Two active employees and one who left, all sharing `tag`."""
    created = []
    for first, position in (("Ana", "Analista"), ("Beto", "=SUM(1;2)"), ("Ciro", "Auxiliar")):
        response = auth_client.post(
            "/employees",
            json=make_employee_payload(first_names=first, last_names=f"{tag} Ruiz", position=position),
        )
        assert response.status_code == 201, response.text
        created.append(response.json())
    terminated = auth_client.post(
        f"/employees/{created[2]['id']}/contracts/terminate",
        json={"end_date": created[2]["start_date"]},
    )
    assert terminated.status_code == 200
    return created


def test_the_export_is_a_csv_download(auth_client: TestClient, people: list[Any], tag: str) -> None:
    response = auth_client.get("/employees/export.csv", params={"q": tag})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["content-disposition"].startswith('attachment; filename="empleados-')
    assert response.headers["cache-control"] == "no-store"
    rows = _rows(response)
    assert rows[0][:2] == ["Nombres", "Apellidos"]
    assert [row[0] for row in rows[1:]] == ["Ana", "Beto", "Ciro"]


def test_the_search_filter_is_respected(auth_client: TestClient, people: list[Any], tag: str) -> None:
    rows = _rows(auth_client.get("/employees/export.csv", params={"q": f"{tag} beto"}))
    assert [row[0] for row in rows[1:]] == ["Beto"]  # CA02


@pytest.mark.parametrize(("status", "names"), [("ACTIVO", ["Ana", "Beto"]), ("INACTIVO", ["Ciro"])])
def test_the_status_filter_is_respected(
    auth_client: TestClient, people: list[Any], tag: str, status: str, names: list[str]
) -> None:
    rows = _rows(auth_client.get("/employees/export.csv", params={"q": tag, "status": status}))
    assert [row[0] for row in rows[1:]] == names  # CA02


def test_formulas_are_neutralized(auth_client: TestClient, people: list[Any], tag: str) -> None:
    rows = _rows(auth_client.get("/employees/export.csv", params={"q": f"{tag} beto"}))
    position = rows[0].index("Cargo")
    assert rows[1][position] == "'=SUM(1;2)"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=1+1", "'=1+1"),
        ("+573001234567", "'+573001234567"),
        ("-5", "'-5"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\tcmd", "'\tcmd"),
        ("Ana María", "Ana María"),
        ("", ""),
    ],
)
def test_neutralize(value: str, expected: str) -> None:
    assert neutralize(value) == expected


@pytest.mark.parametrize(("role", "has_salary"), [(UserRole.ADMIN, True), (UserRole.HR, True), (UserRole.MANAGER, False)])
def test_the_salary_column_depends_on_the_role(
    client: TestClient,
    people: list[Any],
    tag: str,
    db: Session,
    password_hash: str,
    role: UserRole,
    has_salary: bool,
) -> None:
    _login(client, make_user(db, password_hash, role))

    rows = _rows(client.get("/employees/export.csv", params={"q": tag}))

    assert ("Salario" in rows[0]) is has_salary
    assert all(len(row) == len(rows[0]) for row in rows)


def test_an_employee_cannot_export(client: TestClient, db: Session, password_hash: str) -> None:
    _login(client, make_user(db, password_hash, UserRole.EMPLOYEE))
    assert client.get("/employees/export.csv").status_code == 403


def test_the_export_requires_a_session(client: TestClient) -> None:
    assert client.get("/employees/export.csv").status_code == 401


def test_every_export_is_audited(
    auth_client: TestClient, people: list[Any], tag: str, db: Session, hr_user: User
) -> None:
    auth_client.get("/employees/export.csv", params={"q": tag, "status": "ACTIVO"})

    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.action == "EMPLOYEES_EXPORTED", AuditLog.actor_id == hr_user.id
        )
    ).one()
    assert audit.changes["q"] == {"old": None, "new": tag}
    assert audit.changes["status"] == {"old": None, "new": "ACTIVO"}
    assert audit.changes["rows"] == {"old": None, "new": "2"}
    assert audit.changes["with_salary"] == {"old": None, "new": "True"}


def test_too_many_rows_must_be_narrowed(
    auth_client: TestClient, people: list[Any], tag: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(employees_api, "EXPORT_LIMIT", 2)

    response = auth_client.get("/employees/export.csv", params={"q": tag})

    assert response.status_code == 422
    assert response.json()["detail"]["field"] == "q"
