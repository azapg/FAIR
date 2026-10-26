"""Add the transport-neutral Extension execution protocol pins.

Revision ID: 20260714_0026
Revises: 20260714_0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "20260714_0026"
down_revision: str = "20260714_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "extension_installations",
        sa.Column(
            "delivery_mode",
            sa.String(length=32),
            nullable=False,
            server_default="webhook",
        ),
    )
    with op.batch_alter_table("executions") as batch:
        batch.add_column(
            sa.Column("capability_definition_id", sa.UUID(), nullable=True)
        )
        batch.add_column(
            sa.Column("idempotency_key", sa.String(length=255), nullable=True)
        )
        batch.create_foreign_key(
            "fk_executions_capability_definition",
            "capability_definitions",
            ["capability_definition_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_unique_constraint(
            "uq_executions_parent_idempotency_key",
            ["parent_execution_id", "idempotency_key"],
        )
    op.add_column(
        "capability_definitions",
        sa.Column(
            "tool_capabilities",
            sa.JSON().with_variant(
                postgresql.JSONB(astext_type=sa.Text()), "postgresql"
            ),
            nullable=False,
            server_default=sa.text("'[]'"),
        ),
    )
    op.add_column(
        "execution_dispatch_outbox",
        sa.Column("lease_id", sa.UUID(), nullable=True),
    )
    op.create_table(
        "execution_input_artifacts",
        sa.Column("execution_id", sa.UUID(), nullable=False),
        sa.Column("artifact_id", sa.UUID(), nullable=False),
        sa.Column("artifact_version_id", sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["execution_id"], ["executions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"], ["artifact_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("execution_id", "artifact_id"),
    )


def downgrade() -> None:
    raise RuntimeError(
        "20260714_0026 is an intentional destructive cutover that freezes the "
        "Extension protocol and cannot be downgraded"
    )
