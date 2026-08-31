"""Recognize databases migrated by the original LMS PR lineage.

Revision ID: 20260713_0021
Revises: 20260711_0017

PR #204 originally shipped LMS revisions 20260713_0018 through
20260713_0021. During integration those identifiers collided with the
thin-core cutover and the LMS revisions were rebased to 20260714_0021
through 20260714_0024. Existing local databases can still legitimately be
stamped at this historical head, so this no-op branch keeps that state
addressable by Alembic.
"""

from collections.abc import Sequence


revision: str = "20260713_0021"
down_revision: str | None = "20260711_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    raise RuntimeError(
        "20260713_0021 is a historical compatibility marker and cannot be downgraded"
    )
