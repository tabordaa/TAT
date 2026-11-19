"""holidays (HU-4.6)

Revision ID: d8b4f2a6c913
Revises: c6f2d0e8a791
Create Date: 2026-11-18 19:30:00

"""
from collections.abc import Sequence
from datetime import date

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8b4f2a6c913"
down_revision: str | Sequence[str] | None = "c6f2d0e8a791"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Colombian holidays of 2026 and 2027, written out instead of imported from
# app.services.holidays: a migration must insert the same rows forever, even
# if that function changes later. From then on an ADMIN edits the table.
SEED = (
    ("2026-01-01", "Año Nuevo"),
    ("2026-01-12", "Día de los Reyes Magos"),
    ("2026-03-23", "Día de San José"),
    ("2026-04-02", "Jueves Santo"),
    ("2026-04-03", "Viernes Santo"),
    ("2026-05-01", "Día del Trabajo"),
    ("2026-05-18", "Ascensión del Señor"),
    ("2026-06-08", "Corpus Christi"),
    ("2026-06-15", "Sagrado Corazón de Jesús"),
    ("2026-06-29", "San Pedro y San Pablo"),
    ("2026-07-20", "Día de la Independencia"),
    ("2026-08-07", "Batalla de Boyacá"),
    ("2026-08-17", "La Asunción de la Virgen"),
    ("2026-10-12", "Día de la Raza"),
    ("2026-11-02", "Todos los Santos"),
    ("2026-11-16", "Independencia de Cartagena"),
    ("2026-12-08", "Inmaculada Concepción"),
    ("2026-12-25", "Navidad"),
    ("2027-01-01", "Año Nuevo"),
    ("2027-01-11", "Día de los Reyes Magos"),
    ("2027-03-22", "Día de San José"),
    ("2027-03-25", "Jueves Santo"),
    ("2027-03-26", "Viernes Santo"),
    ("2027-05-01", "Día del Trabajo"),
    ("2027-05-10", "Ascensión del Señor"),
    ("2027-05-31", "Corpus Christi"),
    ("2027-06-07", "Sagrado Corazón de Jesús"),
    ("2027-07-05", "San Pedro y San Pablo"),
    ("2027-07-20", "Día de la Independencia"),
    ("2027-08-07", "Batalla de Boyacá"),
    ("2027-08-16", "La Asunción de la Virgen"),
    ("2027-10-18", "Día de la Raza"),
    ("2027-11-01", "Todos los Santos"),
    ("2027-11-15", "Independencia de Cartagena"),
    ("2027-12-08", "Inmaculada Concepción"),
    ("2027-12-25", "Navidad"),
)


def upgrade() -> None:
    # Additive only: a new table and its first rows.
    holidays = op.create_table(
        "holidays",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("day"),
    )
    # Hide the table from Supabase's public Data API (anon key).
    op.execute("ALTER TABLE holidays ENABLE ROW LEVEL SECURITY")
    op.bulk_insert(
        holidays,
        [{"day": date.fromisoformat(day), "name": name} for day, name in SEED],
    )


def downgrade() -> None:
    op.drop_table("holidays")
