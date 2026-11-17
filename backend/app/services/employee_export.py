"""HU-5.2: the employee list as a CSV file for payroll or accounting.

Two things make a CSV export more than "join with commas":

- **Formula injection (CSV injection).** Excel runs a cell that starts with
  = + - or @ as a formula. A name like `=HYPERLINK("http://evil",...)` typed
  into a record would run on the analyst's machine when the file is opened.
  Those cells get a leading apostrophe, which spreadsheets show as text.
- **Excel in Spanish.** It expects `;` as the separator (the comma is the
  decimal mark) and needs the UTF-8 BOM to read tildes and the ñ correctly.
"""

import csv
import io
from collections.abc import Iterable

from app.models.employee import Employee

SEPARATOR = ";"
BOM = "﻿"
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")

STATUS_LABELS = {"ACTIVO": "Activo", "INACTIVO": "Inactivo"}

BASE_COLUMNS = [
    "Nombres",
    "Apellidos",
    "Tipo de documento",
    "Número de documento",
    "Correo",
    "Teléfono",
    "Cargo",
    "Área",
    "Estado",
    "Fecha de ingreso",
    "Fecha de retiro",
]
SALARY_COLUMN = "Salario"


def neutralize(value: str) -> str:
    """Make a cell inert in a spreadsheet: data stays data, never a formula."""
    return f"'{value}" if value.startswith(_FORMULA_STARTS) else value


def _row(employee: Employee, with_salary: bool) -> list[str]:
    cells = [
        employee.first_names,
        employee.last_names,
        employee.document_type.value,
        employee.document_number,
        employee.email,
        employee.phone or "",
        employee.position,
        employee.area,
        STATUS_LABELS.get(employee.status.value, employee.status.value),
        employee.start_date.isoformat(),
        employee.end_date.isoformat() if employee.end_date else "",
    ]
    if with_salary:
        cells.append(f"{employee.salary:.2f}")
    return [neutralize(cell) for cell in cells]


def employees_csv(employees: Iterable[Employee], with_salary: bool) -> str:
    """The whole file as text, BOM included. Salary only when `with_salary`."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=SEPARATOR, lineterminator="\r\n")
    writer.writerow(BASE_COLUMNS + ([SALARY_COLUMN] if with_salary else []))
    for employee in employees:
        writer.writerow(_row(employee, with_salary))
    return BOM + buffer.getvalue()
