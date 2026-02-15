"""add_workflow_plugin_hash_indexes

Revision ID: 20260213_0006
Revises: 20260211_0005
Create Date: 2026-02-13
"""

from __future__ import annotations

from alembic import op


revision = "20260213_0006"
down_revision = "20260211_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_workflows_transcriber_plugin_hash",
        "workflows",
        ["transcriber_plugin_hash"],
        unique=False,
    )
    op.create_index(
        "ix_workflows_grader_plugin_hash",
        "workflows",
        ["grader_plugin_hash"],
        unique=False,
    )
    op.create_index(
        "ix_workflows_validator_plugin_hash",
        "workflows",
        ["validator_plugin_hash"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflows_validator_plugin_hash", table_name="workflows")
    op.drop_index("ix_workflows_grader_plugin_hash", table_name="workflows")
    op.drop_index("ix_workflows_transcriber_plugin_hash", table_name="workflows")
