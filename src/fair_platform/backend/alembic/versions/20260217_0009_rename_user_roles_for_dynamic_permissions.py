"""rename user roles for dynamic permissions

Revision ID: 20260217_0009
Revises: 20260215_0008
Create Date: 2026-02-17
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260217_0009"
down_revision = "20260215_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    users = sa.table(
        "users",
        sa.column("role", sa.String()),
    )
    bind = op.get_bind()
    bind.execute(
        sa.update(users)
        .where(users.c.role == "student")
        .values(role="user")
    )
    bind.execute(
        sa.update(users)
        .where(users.c.role == "professor")
        .values(role="instructor")
    )


def downgrade() -> None:
    users = sa.table(
        "users",
        sa.column("role", sa.String()),
    )
    bind = op.get_bind()
    bind.execute(
        sa.update(users)
        .where(users.c.role == "user")
        .values(role="student")
    )
    bind.execute(
        sa.update(users)
        .where(users.c.role == "instructor")
        .values(role="professor")
    )

