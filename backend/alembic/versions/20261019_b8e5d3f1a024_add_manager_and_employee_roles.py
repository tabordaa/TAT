"""add MANAGER and EMPLOYEE to the user roles (HU 1.6)

Revision ID: b8e5d3f1a024
Revises: a7d4c2e9f013
Create Date: 2026-10-19 09:00:00

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8e5d3f1a024"
down_revision: str | Sequence[str] | None = "a7d4c2e9f013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# users.role is a VARCHAR guarded by a CHECK constraint named "user_role"
# (not a native Postgres ENUM), so adding values means replacing the CHECK.
OLD_ROLES = ("ADMIN", "HR")
NEW_ROLES = ("ADMIN", "MANAGER", "HR", "EMPLOYEE")


def _check(roles: tuple[str, ...]) -> str:
    values = ", ".join(f"'{role}'" for role in roles)
    return f"role IN ({values})"


def upgrade() -> None:
    # Widening the allowed set cannot invalidate existing rows: no data migration.
    op.drop_constraint("user_role", "users", type_="check")
    op.create_check_constraint("user_role", "users", _check(NEW_ROLES))


def downgrade() -> None:
    op.drop_constraint("user_role", "users", type_="check")
    op.create_check_constraint("user_role", "users", _check(OLD_ROLES))
