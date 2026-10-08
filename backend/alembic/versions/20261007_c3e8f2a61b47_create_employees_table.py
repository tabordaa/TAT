"""create employees table (HU-2.1)

Revision ID: c3e8f2a61b47
Revises: 9a1c4e7b2d10
Create Date: 2026-10-07 18:05:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3e8f2a61b47"
down_revision: str | Sequence[str] | None = "9a1c4e7b2d10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, create_constraint=True, length=20)


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_names", sa.String(length=100), nullable=False),
        sa.Column("last_names", sa.String(length=100), nullable=False),
        sa.Column("document_type", _enum("CC", "CE", "PA", "PPT", name="document_type"), nullable=False),
        sa.Column("document_number", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("position", sa.String(length=120), nullable=False),
        sa.Column("area", sa.String(length=120), nullable=True),
        sa.Column(
            "contract_type",
            _enum("INDEFINIDO", "FIJO", "OBRA_LABOR", "APRENDIZAJE", name="contract_type"),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "status",
            _enum("ACTIVO", "INACTIVO", name="employee_status"),
            server_default="ACTIVO",
            nullable=False,
        ),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_employees_end_after_start",
        ),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_type", "document_number", name="uq_employees_document"),
    )
    # Hide the table from Supabase's public Data API (anon key).
    op.execute("ALTER TABLE employees ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("employees")
