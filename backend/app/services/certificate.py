"""HU #163: downloadable employment certificate rendered as a single-page PDF."""

import secrets
from datetime import date
from decimal import Decimal

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from app.core.config import Settings
from app.models.employee import ContractType, DocumentType, Employee

# Mirrors DOCUMENT_TYPES and CONTRACT_TYPES in frontend/src/types/employee.ts.
DOCUMENT_TYPE_LABELS: dict[DocumentType, str] = {
    DocumentType.CC: "Cédula de ciudadanía (CC)",
    DocumentType.CE: "Cédula de extranjería (CE)",
    DocumentType.PA: "Pasaporte (PA)",
    DocumentType.PPT: "Permiso por Protección Temporal (PPT)",
}

CONTRACT_TYPE_LABELS: dict[ContractType, str] = {
    ContractType.INDEFINIDO: "Término indefinido",
    ContractType.FIJO: "Término fijo",
    ContractType.OBRA_LABOR: "Obra o labor",
    ContractType.APRENDIZAJE: "Aprendizaje",
    ContractType.PRESTACION_SERVICIOS: "Prestación de servicios",
}

_MONTHS_ES: tuple[str, ...] = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def generate_verification_code() -> str:
    """Return an uppercase 8-hex verification code formatted as XXXX-XXXX."""
    raw = secrets.token_hex(4).upper()
    return f"{raw[:4]}-{raw[4:]}"


def format_long_date(value: date) -> str:
    """Format a date in Spanish without depending on the OS locale."""
    return f"{value.day} de {_MONTHS_ES[value.month]} de {value.year}"


def format_salary(amount: Decimal) -> str:
    """Format COP salary with dot thousands separators (e.g. '$ 3.500.000')."""
    if amount == amount.to_integral_value():
        grouped = f"{int(amount):,}".replace(",", ".")
        return f"$ {grouped}"
    whole, cents = f"{amount:.2f}".split(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    return f"$ {grouped},{cents}"


def _latin1(text: str) -> str:
    # Core Helvetica supports latin-1 (Spanish accents included); replace any
    # unexpected symbol so a stray character in a record never fails with 500.
    return text.encode("latin-1", "replace").decode("latin-1")


def build_certificate(
    employee: Employee,
    *,
    with_salary: bool,
    code: str,
    issued_on: date,
    settings: Settings,
) -> bytes:
    """Render the employment certificate PDF for an active employee."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    # Leave streams uncompressed so automated checks can inspect text directly.
    pdf.set_compression(False)
    pdf.set_margins(25, 25, 25)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # Letterhead: company name and NIT.
    pdf.set_font("Helvetica", style="B", size=15)
    pdf.set_text_color(31, 95, 191)
    pdf.cell(
        w=0,
        h=8,
        text=_latin1(settings.company_name),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font("Helvetica", style="", size=10)
    pdf.set_text_color(97, 110, 124)
    pdf.cell(
        w=0,
        h=6,
        text=_latin1(f"NIT {settings.company_nit}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(3)
    rule_y = pdf.get_y()
    pdf.set_draw_color(221, 227, 234)
    pdf.set_line_width(0.4)
    pdf.line(25, rule_y, 185, rule_y)

    # Document title.
    pdf.ln(16)
    pdf.set_font("Helvetica", style="B", size=14)
    pdf.set_text_color(31, 41, 51)
    pdf.cell(
        w=0,
        h=10,
        text="CERTIFICADO LABORAL",
        align="C",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # Certification body.
    full_name = f"{employee.first_names} {employee.last_names}"
    document_label = DOCUMENT_TYPE_LABELS.get(
        employee.document_type, employee.document_type.value
    )
    contract_label = CONTRACT_TYPE_LABELS.get(
        employee.contract_type, employee.contract_type.value
    )
    body = (
        f"La {settings.certificate_signer} de {settings.company_name} certifica que "
        f"{full_name}, identificado(a) con {document_label} No. {employee.document_number}, "
        f"labora en la empresa desde el {format_long_date(employee.start_date)} "
        f"con contrato a {contract_label}, desempeñando el cargo de {employee.position} "
        f"en el área de {employee.area}"
    )
    if with_salary:
        body += f", devengando un salario mensual de {format_salary(employee.salary)}"
    body += "."

    pdf.ln(10)
    pdf.set_font("Helvetica", style="", size=11)
    pdf.set_text_color(31, 41, 51)
    pdf.multi_cell(
        w=0,
        h=7,
        text=_latin1(body),
        align="L",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # Expedition line.
    pdf.ln(8)
    expedition = f"Se expide en {settings.company_city}, el {format_long_date(issued_on)}."
    pdf.multi_cell(
        w=0,
        h=7,
        text=_latin1(expedition),
        align="L",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # Signature block.
    pdf.ln(28)
    sign_y = pdf.get_y()
    pdf.set_draw_color(31, 41, 51)
    pdf.set_line_width(0.35)
    pdf.line(25, sign_y, 95, sign_y)
    pdf.ln(3)
    pdf.set_font("Helvetica", style="B", size=11)
    pdf.set_text_color(31, 41, 51)
    pdf.cell(
        w=0,
        h=6,
        text=_latin1(settings.certificate_signer),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_font("Helvetica", style="", size=10)
    pdf.set_text_color(97, 110, 124)
    pdf.cell(
        w=0,
        h=6,
        text=_latin1(settings.company_name),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    # Verification footer pinned at the bottom of the single page.
    pdf.set_auto_page_break(auto=False)
    if pdf.get_y() < 260:
        pdf.set_y(-28)
    else:
        pdf.ln(10)
    footer_y = pdf.get_y()
    pdf.set_draw_color(221, 227, 234)
    pdf.set_line_width(0.3)
    pdf.line(25, footer_y, 185, footer_y)
    pdf.ln(4)
    pdf.set_font("Helvetica", style="", size=9)
    pdf.set_text_color(97, 110, 124)
    pdf.cell(
        w=0,
        h=5,
        text=_latin1(f"Código de verificación: {code}"),
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    return bytes(pdf.output())
