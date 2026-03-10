"""Add extension client credential table for extension API auth.

Revision ID: 20260228_0013
Revises: 20260224_0012
Create Date: 2026-02-28
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260228_0013"
down_revision = "20260224_0012"
branch_labels = None
depends_on = None


def _json_document_type() -> sa.JSON:
    return sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    op.create_table(
        "extension_clients",
        sa.Column("extension_id", sa.String(), nullable=False),
        sa.Column("secret_hash", sa.String(), nullable=False),
        sa.Column("scopes", _json_document_type(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("extension_id"),
    )


def downgrade() -> None:
    op.drop_table("extension_clients")
