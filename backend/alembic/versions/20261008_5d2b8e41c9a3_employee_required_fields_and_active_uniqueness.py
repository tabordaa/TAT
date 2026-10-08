"""employee salary, required email/area and active-only uniqueness (HU-2.1)

Revision ID: 5d2b8e41c9a3
Revises: c3e8f2a61b47
Create Date: 2026-10-08 01:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d2b8e41c9a3"
down_revision: str | Sequence[str] | None = "c3e8f2a61b47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACTIVE_ONLY = sa.text("status = 'ACTIVO'")


def upgrade() -> None:
    # NOT NULL without a default: fails loudly if old rows lack these values,
    # instead of silently inventing data.
    op.add_column("employees", sa.Column("salary", sa.Numeric(12, 2), nullable=False))
    op.create_check_constraint("ck_employees_salary_positive", "employees", "salary > 0")
    op.alter_column("employees", "email", existing_type=sa.String(255), nullable=False)
    op.alter_column("employees", "area", existing_type=sa.String(120), nullable=False)

    # Uniqueness only among ACTIVO employees (allows rehiring later).
    op.drop_constraint("uq_employees_document", "employees", type_="unique")
    op.create_index(
        "uq_employees_active_document",
        "employees",
        ["document_type", "document_number"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )
    op.create_index(
        "uq_employees_active_email",
        "employees",
        ["email"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )


def downgrade() -> None:
    op.drop_index("uq_employees_active_email", table_name="employees")
    op.drop_index("uq_employees_active_document", table_name="employees")
    op.create_unique_constraint(
        "uq_employees_document", "employees", ["document_type", "document_number"]
    )
    op.alter_column("employees", "area", existing_type=sa.String(120), nullable=True)
    op.alter_column("employees", "email", existing_type=sa.String(255), nullable=True)
    op.drop_constraint("ck_employees_salary_positive", "employees", type_="check")
    op.drop_column("employees", "salary")
