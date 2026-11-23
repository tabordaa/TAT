"""HU #163: downloadable employment certificate for the signed-in employee."""

import re
import uuid
from collections.abc import Callable
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import today
from app.core.config import get_settings
from app.models.audit_log import AuditAction, AuditLog
from app.models.employee import Employee, EmployeeStatus, EmploymentContract
from app.models.user import User, UserRole
from app.services.certificate import (
    format_long_date,
    format_salary,
    generate_verification_code,
)
from tests.conftest import TEST_PASSWORD, make_user

PayloadFactory = Callable[..., dict[str, Any]]


def _login(client: TestClient, user: User) -> None:
    client.cookies.clear()
    response = client.post(
        "/auth/login", json={"email": user.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200, response.text


def _pdf_text(data: bytes) -> str:
    """Extract linear text from an uncompressed fpdf2 PDF stream."""
    raw = data.decode("latin-1")
    chunks: list[str] = []
    for match in re.finditer(
        r"\(([^()\\]*(?:\\.[^()\\]*)*)\)\s*Tj|\[(.*?)\]\s*TJ", raw, re.DOTALL
    ):
        if match.group(1) is not None:
            chunks.append(match.group(1))
        else:
            parts = re.findall(r"\(([^()\\]*(?:\\.[^()\\]*)*)\)", match.group(2))
            chunks.append("".join(parts))
    text = " ".join(chunks)
    return text.replace(r"\(", "(").replace(r"\)", ")").replace(r"\\", "\\")


@pytest.fixture
def employee_record(
    auth_client: TestClient, make_employee_payload: PayloadFactory
) -> dict[str, Any]:
    response = auth_client.post(
        "/employees",
        json=make_employee_payload(
            first_names="María José",
            last_names="Gómez Ríos",
            position="Ingeniera de soporte",
            area="Tecnología",
            salary="4250000.00",
            contract_type="INDEFINIDO",
            start_date="2025-03-10",
        ),
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def user(
    db: Session, password_hash: str, employee_record: dict[str, Any]
) -> User:
    linked = make_user(db, password_hash, UserRole.EMPLOYEE)
    linked.employee_id = uuid.UUID(employee_record["id"])
    db.commit()
    return linked


@pytest.fixture
def me(client: TestClient, user: User) -> TestClient:
    _login(client, user)
    return client


# --- CA01 & CA04: PDF download, headers, content and audit -------------------


def test_downloads_pdf_with_expected_headers_and_content(
    me: TestClient,
    db: Session,
    user: User,
    employee_record: dict[str, Any],
) -> None:
    response = me.get("/me/employment-certificate.pdf")

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")
    assert response.headers["content-type"] == "application/pdf"
    expected_filename = f"certificado-laboral-{employee_record['document_number']}.pdf"
    assert (
        response.headers["content-disposition"]
        == f'attachment; filename="{expected_filename}"'
    )
    assert response.headers["cache-control"] == "no-store"

    audit = db.scalars(
        select(AuditLog).where(
            AuditLog.entity_id == uuid.UUID(employee_record["id"]),
            AuditLog.action == AuditAction.CERTIFICATE_ISSUED.value,
        )
    ).one()
    code = audit.changes["code"]["new"]
    assert audit.actor_id == user.id
    assert audit.entity_type == "employee"
    assert audit.changes["code"]["old"] is None
    assert audit.changes["with_salary"] == {"old": None, "new": "False"}
    assert code is not None
    assert re.fullmatch(r"[0-9A-F]{4}-[0-9A-F]{4}", code)

    text = _pdf_text(response.content)
    settings = get_settings()
    assert settings.company_name in text
    assert settings.company_nit in text
    assert "CERTIFICADO LABORAL" in text
    assert "María José Gómez Ríos" in text
    assert "Cédula de ciudadanía (CC)" in text
    assert employee_record["document_number"] in text
    assert "10 de marzo de 2025" in text
    assert "Término indefinido" in text
    assert "Ingeniera de soporte" in text
    assert "Tecnología" in text
    assert format_long_date(today()) in text
    assert f"Código de verificación: {code}" in text


# --- CA02: optional salary ---------------------------------------------------


def test_with_salary_true_includes_salary_and_false_omits_it(
    me: TestClient, db: Session, employee_record: dict[str, Any]
) -> None:
    without_salary = me.get(
        "/me/employment-certificate.pdf", params={"with_salary": "false"}
    )
    with_salary = me.get(
        "/me/employment-certificate.pdf", params={"with_salary": "true"}
    )

    assert without_salary.status_code == 200
    assert with_salary.status_code == 200

    text_without = _pdf_text(without_salary.content)
    text_with = _pdf_text(with_salary.content)

    assert "$ 4.250.000" not in text_without
    assert "devengando" not in text_without
    assert "devengando un salario mensual de $ 4.250.000" in text_with

    rows = list(
        db.scalars(
            select(AuditLog)
            .where(
                AuditLog.entity_id == uuid.UUID(employee_record["id"]),
                AuditLog.action == AuditAction.CERTIFICATE_ISSUED.value,
            )
            .order_by(AuditLog.created_at)
        )
    )
    assert len(rows) == 2
    assert {row.changes["with_salary"]["new"] for row in rows} == {"False", "True"}


# --- CA03: access rules, active status and contract in force -----------------


def test_requires_a_session(client: TestClient) -> None:
    assert client.get("/me/employment-certificate.pdf").status_code == 401


def test_temporary_password_cannot_download_certificate(
    client: TestClient, db: Session, user: User
) -> None:
    user.must_change_password = True
    db.commit()
    _login(client, user)

    assert client.get("/me/employment-certificate.pdf").status_code == 403


def test_account_without_employee_gets_404(
    client: TestClient, db: Session, password_hash: str
) -> None:
    _login(client, make_user(db, password_hash, UserRole.EMPLOYEE))
    assert client.get("/me/employment-certificate.pdf").status_code == 404


def test_inactive_employee_gets_409(
    me: TestClient, db: Session, employee_record: dict[str, Any]
) -> None:
    employee = db.get(Employee, uuid.UUID(employee_record["id"]))
    assert employee is not None
    employee.status = EmployeeStatus.INACTIVO
    db.commit()

    response = me.get("/me/employment-certificate.pdf")

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "status"


def test_active_employee_without_contract_in_force_gets_409(
    me: TestClient, db: Session, employee_record: dict[str, Any]
) -> None:
    contracts = list(
        db.scalars(
            select(EmploymentContract).where(
                EmploymentContract.employee_id == uuid.UUID(employee_record["id"])
            )
        )
    )
    for contract in contracts:
        contract.terminated_on = contract.start_date
    db.commit()

    response = me.get("/me/employment-certificate.pdf")

    assert response.status_code == 409
    assert response.json()["detail"]["field"] == "status"


# --- formatting helpers ------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (date(2026, 1, 1), "1 de enero de 2026"),
        (date(2026, 12, 31), "31 de diciembre de 2026"),
    ],
)
def test_format_long_date(value: date, expected: str) -> None:
    assert format_long_date(value) == expected


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("3500000.00"), "$ 3.500.000"),
        (Decimal("2500000.50"), "$ 2.500.000,50"),
    ],
)
def test_format_salary(amount: Decimal, expected: str) -> None:
    assert format_salary(amount) == expected


def test_generate_verification_code_format() -> None:
    assert re.fullmatch(r"[0-9A-F]{4}-[0-9A-F]{4}", generate_verification_code())
