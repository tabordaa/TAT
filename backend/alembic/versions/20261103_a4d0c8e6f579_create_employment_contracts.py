"""employment contract history and the Prestacion de Servicios type (HU-3.1)

Revision ID: a4d0c8e6f579
Revises: f3c9b7d5e468
Create Date: 2026-11-03 22:30:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4d0c8e6f579"
down_revision: str | Sequence[str] | None = "f3c9b7d5e468"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_TYPES = ("INDEFINIDO", "FIJO", "OBRA_LABOR", "APRENDIZAJE")
NEW_TYPES = (*OLD_TYPES, "PRESTACION_SERVICIOS")


def _check(types: tuple[str, ...]) -> str:
    values = ", ".join(f"'{value}'" for value in types)
    return f"contract_type IN ({values})"


def upgrade() -> None:
    # Widening the allowed set cannot invalidate existing rows.
    op.drop_constraint("contract_type", "employees", type_="check")
    op.create_check_constraint("contract_type", "employees", _check(NEW_TYPES))

    op.create_table(
        "employment_contracts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column(
            "contract_type",
            sa.Enum(
                *NEW_TYPES,
                name="contract_type",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("terminated_on", sa.Date(), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_contracts_end_after_start",
        ),
        sa.CheckConstraint(
            "terminated_on IS NULL OR terminated_on >= start_date",
            name="ck_contracts_terminated_after_start",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_employment_contracts_employee_start",
        "employment_contracts",
        ["employee_id", "start_date"],
    )
    # Hide the table from Supabase's public Data API (anon key).
    op.execute("ALTER TABLE employment_contracts ENABLE ROW LEVEL SECURITY")

    # Every existing employee starts with their current contract as the history.
    # Inserts only: no existing row changes.
    op.execute(
        """
        INSERT INTO employment_contracts (
            id, employee_id, contract_type, start_date, end_date,
            terminated_on, created_by_id, created_at
        )
        SELECT
            gen_random_uuid(), id, contract_type, start_date, end_date,
            CASE WHEN status = 'INACTIVO' THEN COALESCE(end_date, start_date) END,
            created_by_id, created_at
        FROM employees
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_employment_contracts_employee_start", table_name="employment_contracts"
    )
    op.drop_table("employment_contracts")
    # Rows using the new type would have to be reassigned by hand before this.
    op.drop_constraint("contract_type", "employees", type_="check")
    op.create_check_constraint("contract_type", "employees", _check(OLD_TYPES))
