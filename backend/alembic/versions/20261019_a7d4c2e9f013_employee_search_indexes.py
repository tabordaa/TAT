"""employee search indexes (HU-2.2)

Revision ID: a7d4c2e9f013
Revises: 5d2b8e41c9a3
Create Date: 2026-10-19 08:00:00

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7d4c2e9f013"
down_revision: str | Sequence[str] | None = "5d2b8e41c9a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Columns searched with ILIKE '%term%' (a plain B-tree cannot serve that).
TRIGRAM_COLUMNS = ("first_names", "last_names", "document_number")


def upgrade() -> None:
    # Supabase keeps extensions in their own schema, out of the public API.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA extensions")

    # Trigram GIN indexes make contains-searches (ILIKE '%ana%') index-assisted.
    # The operator class is schema-qualified so it does not depend on search_path.
    for column in TRIGRAM_COLUMNS:
        op.execute(
            f"CREATE INDEX ix_employees_{column}_trgm ON employees "
            f"USING gin ({column} extensions.gin_trgm_ops)"
        )

    # Serves the status filter together with the directory's sort order.
    op.create_index(
        "ix_employees_status_last_first",
        "employees",
        ["status", "last_names", "first_names"],
    )


def downgrade() -> None:
    op.drop_index("ix_employees_status_last_first", table_name="employees")
    for column in TRIGRAM_COLUMNS:
        op.execute(f"DROP INDEX IF EXISTS ix_employees_{column}_trgm")
    # The extension is left installed: other objects may come to depend on it.
