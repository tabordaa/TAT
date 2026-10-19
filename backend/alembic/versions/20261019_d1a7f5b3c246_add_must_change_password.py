"""users.must_change_password for temporary passwords (HU-1.4)

Revision ID: d1a7f5b3c246
Revises: c9f6e4a2b135
Create Date: 2026-10-19 10:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1a7f5b3c246"
down_revision: str | Sequence[str] | None = "c9f6e4a2b135"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # server_default fills existing rows with false, so NOT NULL is valid at once
    # and current users are not forced to change anything.
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
