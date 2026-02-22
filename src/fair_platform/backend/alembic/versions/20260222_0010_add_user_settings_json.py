"""add user settings json/jsonb column

Revision ID: 20260222_0010
Revises: 20260217_0009
Create Date: 2026-02-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20260222_0010"
down_revision = "20260217_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "settings",
            sa.JSON().with_variant(postgresql.JSONB, "postgresql"),
            nullable=True,
        ),
    )

    users = sa.table(
        "users",
        sa.column("settings", sa.JSON()),
    )
    op.execute(sa.update(users).where(users.c.settings.is_(None)).values(settings={}))
    op.alter_column("users", "settings", nullable=False)


def downgrade() -> None:
    op.drop_column("users", "settings")
