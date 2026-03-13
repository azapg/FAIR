"""add users.is_verified flag

Revision ID: 20260313_0016
Revises: 20260307_0015
Create Date: 2026-03-13
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260313_0016"
down_revision = "20260307_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {col["name"] for col in inspector.get_columns("users")}
    if "is_verified" in columns:
        return

    op.add_column("users", sa.Column("is_verified", sa.Boolean(), nullable=True))
    op.execute(sa.text("UPDATE users SET is_verified = 1 WHERE is_verified IS NULL"))

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("users") as batch_op:
            batch_op.alter_column(
                "is_verified",
                existing_type=sa.Boolean(),
                nullable=False,
                server_default=sa.text("0"),
            )
    else:
        op.alter_column(
            "users",
            "is_verified",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        )


def downgrade() -> None:
    op.drop_column("users", "is_verified")
