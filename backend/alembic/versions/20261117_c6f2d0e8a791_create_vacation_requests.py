"""vacation requests (HU-4.1 to 4.4)

Revision ID: c6f2d0e8a791
Revises: b5e1c9d7f680
Create Date: 2026-11-17 02:15:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c6f2d0e8a791"
down_revision: str | Sequence[str] | None = "b5e1c9d7f680"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STATUSES = ("PENDIENTE", "APROBADA", "RECHAZADA", "CANCELADA")


def upgrade() -> None:
    # Additive only: a new table, no existing row changes.
    op.create_table(
        "vacation_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("employee_id", sa.Uuid(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("business_days", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                *STATUSES,
                name="vacation_status",
                native_enum=False,
                create_constraint=True,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column("requested_by_id", sa.Uuid(), nullable=False),
        sa.Column("decided_by_id", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("end_date >= start_date", name="ck_vacation_requests_dates"),
        sa.CheckConstraint("business_days > 0", name="ck_vacation_requests_business_days"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["requested_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["decided_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_vacation_requests_employee_status",
        "vacation_requests",
        ["employee_id", "status"],
    )
    op.create_index(
        "ix_vacation_requests_status_start",
        "vacation_requests",
        ["status", "start_date"],
    )
    # Hide the table from Supabase's public Data API (anon key).
    op.execute("ALTER TABLE vacation_requests ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index("ix_vacation_requests_status_start", table_name="vacation_requests")
    op.drop_index("ix_vacation_requests_employee_status", table_name="vacation_requests")
    op.drop_table("vacation_requests")
