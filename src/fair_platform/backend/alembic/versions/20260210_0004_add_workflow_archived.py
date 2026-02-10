"""add_workflow_archived

Revision ID: 20260210_0004
Revises: 39361b552edd
Create Date: 2026-02-10 11:25:00.000000
"""

from __future__ import annotations

from alembic import op  # type: ignore
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260210_0004"
down_revision = "39361b552edd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "workflows",
        sa.Column(
            "archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    with op.batch_alter_table("workflows", schema=None) as batch_op:
        batch_op.drop_column("archived")
