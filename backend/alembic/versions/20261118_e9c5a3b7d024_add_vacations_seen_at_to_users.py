"""add vacations_seen_at to users (HU-4.7)

Revision ID: e9c5a3b7d024
Revises: d8b4f2a6c913
Create Date: 2026-11-18 20:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9c5a3b7d024"
down_revision: str | Sequence[str] | None = "d8b4f2a6c913"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Additive and nullable: existing accounts simply have never looked yet.
    op.add_column(
        "users",
        sa.Column("vacations_seen_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "vacations_seen_at")
