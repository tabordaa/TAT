"""optional link from users to employees (HU 1.6)

Revision ID: c9f6e4a2b135
Revises: b8e5d3f1a024
Create Date: 2026-10-19 09:30:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9f6e4a2b135"
down_revision: str | Sequence[str] | None = "b8e5d3f1a024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Nullable and without a default: existing users simply have no link, so
    # no data migration. No new table, so RLS is already enabled on both sides.
    op.add_column("users", sa.Column("employee_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_users_employee_id",
        "users",
        "employees",
        ["employee_id"],
        ["id"],
        ondelete="SET NULL",
    )
    # One account per employee (many NULLs are allowed by Postgres).
    op.create_unique_constraint("uq_users_employee_id", "users", ["employee_id"])


def downgrade() -> None:
    op.drop_constraint("uq_users_employee_id", "users", type_="unique")
    op.drop_constraint("fk_users_employee_id", "users", type_="foreignkey")
    op.drop_column("users", "employee_id")
