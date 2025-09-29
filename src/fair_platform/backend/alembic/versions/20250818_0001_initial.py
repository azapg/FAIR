"""Initial users table

Revision ID: 20250818_0001
Revises:
Create Date: 2025-08-18
"""

from __future__ import annotations
from alembic import op  # type: ignore
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20250818_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create Enum type for portability (will be inline for SQLite)
    user_role_enum = sa.Enum("professor", "student", "admin", name="user_role")
    user_role_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False, server_default="student"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_id", "users", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_id", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    # Drop enum if supported (skip for SQLite which stores inline)
    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        sa.Enum(name="user_role").drop(bind, checkfirst=True)
