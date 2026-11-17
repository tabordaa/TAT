"""salary history (HU-2.4 and HU-2.5)

Revision ID: b5e1c9d7f680
Revises: a4d0c8e6f579
Create Date: 2026-11-17 01:50:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b5e1c9d7f680"
down_revision: str | Sequence[str] | None = "a4d0c8e6f579"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Additive only: a new table, no existing row changes.
    op.create_table(
        "salary_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("old_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("new_salary", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("changed_by_id", sa.Uuid(), nullable=False),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "old_salary > 0 AND new_salary > 0", name="ck_salary_changes_positive"
        ),
        sa.CheckConstraint("old_salary <> new_salary", name="ck_salary_changes_differs"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["changed_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_salary_changes_employee_changed",
        "salary_changes",
        ["employee_id", "changed_at"],
    )
    # Hide the table from Supabase's public Data API (anon key).
    op.execute("ALTER TABLE salary_changes ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_salary_changes_employee_changed", table_name="salary_changes")
    op.drop_table("salary_changes")
