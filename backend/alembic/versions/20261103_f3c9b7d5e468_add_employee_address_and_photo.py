"""add employee address and photo path (HU-2.7)

Revision ID: f3c9b7d5e468
Revises: e2b8a6c4d357
Create Date: 2026-11-03 22:00:00

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3c9b7d5e468"
down_revision: str | Sequence[str] | None = "e2b8a6c4d357"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("address", sa.String(length=200), nullable=True))
    op.add_column("employees", sa.Column("photo_path", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("employees", "photo_path")
    op.drop_column("employees", "address")
