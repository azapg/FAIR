"""Add recoverable leases to course copy jobs.

Revision ID: 20260812_0034
Revises: 20260812_0033
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "20260812_0034"
down_revision: str = "20260812_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("course_copy_jobs") as batch_op:
        batch_op.add_column(sa.Column("lease_token", sa.UUID(), nullable=True))
        batch_op.add_column(
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("course_copy_jobs") as batch_op:
        batch_op.drop_column("lease_expires_at")
        batch_op.drop_column("lease_token")
