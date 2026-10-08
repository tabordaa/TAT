"""add token_version to users (HU-1.3: server-side logout)

Revision ID: 9a1c4e7b2d10
Revises: f3f41742dcf6
Create Date: 2026-10-07 18:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9a1c4e7b2d10"
down_revision: str | Sequence[str] | None = "f3f41742dcf6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default fills existing rows with 0 so NOT NULL is valid immediately.
    op.add_column(
        "users",
        sa.Column("token_version", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "token_version")
