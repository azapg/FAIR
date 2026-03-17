"""Split artifact storage metadata into derivative records.

Revision ID: 20260307_0013
Revises: 20260313_0016
Create Date: 2026-03-07
"""

from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


revision = "20260307_0013"
down_revision = "20260313_0016"
branch_labels = None
depends_on = None


def _uuid_type(dialect_name: str):
    if dialect_name == "postgresql":
        from sqlalchemy.dialects import postgresql

        return postgresql.UUID(as_uuid=False)
    return sa.String(length=36)


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    uuid_col = _uuid_type(dialect_name)

    op.create_table(
        "artifact_derivatives",
        sa.Column("id", uuid_col, primary_key=True, nullable=False),
        sa.Column("artifact_id", uuid_col, sa.ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("derivative_type", sa.String(), nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=False),
        sa.Column("mime_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    metadata = sa.MetaData()
    artifacts = sa.Table(
        "artifacts",
        metadata,
        sa.Column("id", uuid_col),
        sa.Column("mime", sa.Text()),
        sa.Column("storage_path", sa.Text()),
        sa.Column("storage_type", sa.Text()),
        sa.Column("created_at", sa.TIMESTAMP()),
        sa.Column("updated_at", sa.TIMESTAMP()),
    )
    artifact_derivatives = sa.Table(
        "artifact_derivatives",
        metadata,
        sa.Column("id", uuid_col),
        sa.Column("artifact_id", uuid_col),
        sa.Column("derivative_type", sa.String()),
        sa.Column("storage_uri", sa.Text()),
        sa.Column("mime_type", sa.String()),
        sa.Column("created_at", sa.TIMESTAMP()),
        sa.Column("updated_at", sa.TIMESTAMP()),
    )

    rows = bind.execute(
        sa.select(
            artifacts.c.id,
            artifacts.c.mime,
            artifacts.c.storage_path,
            artifacts.c.storage_type,
            artifacts.c.created_at,
            artifacts.c.updated_at,
        )
    ).fetchall()

    derivative_rows = []
    for row in rows:
        if not row.storage_path:
            continue
        storage_type = (row.storage_type or "local").strip() or "local"
        derivative_rows.append(
            {
                "id": str(uuid.uuid4()),
                "artifact_id": row.id,
                "derivative_type": "original",
                "storage_uri": f"{storage_type}://{str(row.storage_path).lstrip('/')}",
                "mime_type": row.mime or "application/octet-stream",
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    if derivative_rows:
        op.bulk_insert(artifact_derivatives, derivative_rows)

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.drop_column("mime")
        batch_op.drop_column("storage_path")
        batch_op.drop_column("storage_type")


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name
    uuid_col = _uuid_type(dialect_name)

    with op.batch_alter_table("artifacts") as batch_op:
        batch_op.add_column(sa.Column("mime", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("storage_path", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("storage_type", sa.Text(), nullable=True))

    metadata = sa.MetaData()
    artifacts = sa.Table(
        "artifacts",
        metadata,
        sa.Column("id", uuid_col),
        sa.Column("mime", sa.Text()),
        sa.Column("storage_path", sa.Text()),
        sa.Column("storage_type", sa.Text()),
    )
    artifact_derivatives = sa.Table(
        "artifact_derivatives",
        metadata,
        sa.Column("artifact_id", uuid_col),
        sa.Column("derivative_type", sa.String()),
        sa.Column("storage_uri", sa.Text()),
        sa.Column("mime_type", sa.String()),
    )

    originals = bind.execute(
        sa.select(
            artifact_derivatives.c.artifact_id,
            artifact_derivatives.c.storage_uri,
            artifact_derivatives.c.mime_type,
        ).where(artifact_derivatives.c.derivative_type == "original")
    ).fetchall()

    for row in originals:
        storage_type, storage_path = str(row.storage_uri).split("://", 1)
        bind.execute(
            artifacts.update()
            .where(artifacts.c.id == row.artifact_id)
            .values(
                mime=row.mime_type or "application/octet-stream",
                storage_path=storage_path,
                storage_type=storage_type,
            )
        )

    if bind.dialect.name == "sqlite":
        with op.batch_alter_table("artifacts") as batch_op:
            batch_op.alter_column("mime", existing_type=sa.Text(), nullable=False)
            batch_op.alter_column("storage_path", existing_type=sa.Text(), nullable=False)
            batch_op.alter_column("storage_type", existing_type=sa.Text(), nullable=False)
    else:
        op.alter_column("artifacts", "mime", existing_type=sa.Text(), nullable=False)
        op.alter_column("artifacts", "storage_path", existing_type=sa.Text(), nullable=False)
        op.alter_column("artifacts", "storage_type", existing_type=sa.Text(), nullable=False)

    op.drop_table("artifact_derivatives")
