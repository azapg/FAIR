"""remove legacy sdk tables and workflow plugin columns

Revision ID: 20260307_0015
Revises: 20260305_0014
Create Date: 2026-03-07 12:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "20260307_0015"
down_revision = "20260305_0014"
branch_labels = None
depends_on = None


def _json_document_type() -> sa.JSON:
    return sa.JSON().with_variant(JSONB, "postgresql")


def upgrade() -> None:
    with op.batch_alter_table("workflows") as batch_op:
        batch_op.drop_index("ix_workflows_transcriber_plugin_hash")
        batch_op.drop_index("ix_workflows_grader_plugin_hash")
        batch_op.drop_index("ix_workflows_validator_plugin_hash")
        batch_op.drop_constraint("fk_workflows_transcriber_hash", type_="foreignkey")
        batch_op.drop_constraint("fk_workflows_grader_hash", type_="foreignkey")
        batch_op.drop_constraint("fk_workflows_validator_hash", type_="foreignkey")
        batch_op.drop_column("transcriber_plugin_hash")
        batch_op.drop_column("transcriber_settings")
        batch_op.drop_column("grader_plugin_hash")
        batch_op.drop_column("grader_settings")
        batch_op.drop_column("validator_plugin_hash")
        batch_op.drop_column("validator_settings")

    op.drop_table("plugins")


def downgrade() -> None:
    op.create_table(
        "plugins",
        sa.Column("hash", sa.String(), nullable=False),
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("author", sa.String(), nullable=False),
        sa.Column("author_email", sa.String(), nullable=True),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("meta", _json_document_type(), nullable=True),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("settings_schema", _json_document_type(), nullable=True),
        sa.PrimaryKeyConstraint("hash"),
    )

    with op.batch_alter_table("workflows") as batch_op:
        batch_op.add_column(
            sa.Column("validator_settings", _json_document_type(), nullable=True)
        )
        batch_op.add_column(sa.Column("validator_plugin_hash", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("grader_settings", _json_document_type(), nullable=True)
        )
        batch_op.add_column(sa.Column("grader_plugin_hash", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("transcriber_settings", _json_document_type(), nullable=True)
        )
        batch_op.add_column(sa.Column("transcriber_plugin_hash", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_workflows_transcriber_hash", "plugins", ["transcriber_plugin_hash"], ["hash"]
        )
        batch_op.create_foreign_key(
            "fk_workflows_grader_hash", "plugins", ["grader_plugin_hash"], ["hash"]
        )
        batch_op.create_foreign_key(
            "fk_workflows_validator_hash", "plugins", ["validator_plugin_hash"], ["hash"]
        )
        batch_op.create_index(
            "ix_workflows_transcriber_plugin_hash", ["transcriber_plugin_hash"], unique=False
        )
        batch_op.create_index(
            "ix_workflows_grader_plugin_hash", ["grader_plugin_hash"], unique=False
        )
        batch_op.create_index(
            "ix_workflows_validator_plugin_hash", ["validator_plugin_hash"], unique=False
        )
