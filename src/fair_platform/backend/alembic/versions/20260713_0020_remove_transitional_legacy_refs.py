"""Remove the transitional Execution legacy-reference table.

Revision ID: 20260713_0020
Revises: 20260713_0019
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260713_0020"
down_revision: str | None = "20260713_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("execution_legacy_refs")


def downgrade() -> None:
    raise RuntimeError(
        "20260713_0020 is an intentional destructive cutover and cannot be downgraded"
    )
