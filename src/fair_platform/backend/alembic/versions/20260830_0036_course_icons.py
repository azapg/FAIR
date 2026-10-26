"""Add a persistent visual icon to courses.

Revision ID: 20260830_0036
Revises: 20260823_0035
"""

import sqlalchemy as sa
from alembic import op


revision: str = "20260830_0036"
down_revision: str = "20260823_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "courses",
        sa.Column(
            "icon_key",
            sa.String(64),
            nullable=False,
            server_default="book-open",
        ),
    )


def downgrade() -> None:
    op.drop_column("courses", "icon_key")
