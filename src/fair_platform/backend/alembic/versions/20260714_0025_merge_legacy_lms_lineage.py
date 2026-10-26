"""Merge the historical LMS and integrated thin-core lineages.

Revision ID: 20260714_0025
Revises: 20260714_0024, 20260713_0021
"""

from collections.abc import Sequence


revision: str = "20260714_0025"
down_revision: tuple[str, str] = ("20260714_0024", "20260713_0021")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError(
        "20260714_0025 merges an intentional destructive cutover and cannot be downgraded"
    )
