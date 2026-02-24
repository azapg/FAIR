"""Reconcile plugin key constraints and convert JSON columns to JSONB on PostgreSQL.

Revision ID: 20260224_0011
Revises: 20260222_0010
Create Date: 2026-02-24
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260224_0011"
down_revision = "20260222_0010"
branch_labels = None
depends_on = None


JSON_COLUMNS: tuple[tuple[str, str], ...] = (
    ("artifacts", "meta"),
    ("assignments", "max_grade"),
    ("plugins", "meta"),
    ("plugins", "settings_schema"),
    ("submission_events", "details"),
    ("submission_results", "grading_meta"),
    ("users", "settings"),
    ("workflows", "transcriber_settings"),
    ("workflows", "grader_settings"),
    ("workflows", "validator_settings"),
    ("workflow_runs", "logs"),
    ("rubrics", "content"),
)


def _is_postgresql(bind) -> bool:
    return bind.dialect.name == "postgresql"


def _pg_column_type(bind, table_name: str, column_name: str) -> str | None:
    row = bind.execute(
        sa.text(
            """
            SELECT data_type
            FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = :table_name
              AND column_name = :column_name
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    ).first()
    return row[0] if row else None


def _convert_pg_column(bind, table_name: str, column_name: str, target_type: str) -> None:
    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" '
            f'ALTER COLUMN "{column_name}" TYPE {target_type} '
            f'USING "{column_name}"::{target_type}'
        )
    )


def _reconcile_plugin_key_constraints(bind) -> None:
    inspector = sa.inspect(bind)
    pk = inspector.get_pk_constraint("plugins")
    pk_cols = pk.get("constrained_columns", []) or []
    pk_name = pk.get("name")

    if pk_cols == ["hash"]:
        return

    if pk_name:
        op.drop_constraint(pk_name, "plugins", type_="primary")

    op.create_primary_key("pk_plugins_hash", "plugins", ["hash"])


def upgrade() -> None:
    bind = op.get_bind()

    if _is_postgresql(bind):
        _reconcile_plugin_key_constraints(bind)

        for table_name, column_name in JSON_COLUMNS:
            current_type = _pg_column_type(bind, table_name, column_name)
            if current_type and current_type != "jsonb":
                _convert_pg_column(bind, table_name, column_name, "jsonb")


def downgrade() -> None:
    bind = op.get_bind()

    if _is_postgresql(bind):
        for table_name, column_name in JSON_COLUMNS:
            current_type = _pg_column_type(bind, table_name, column_name)
            if current_type == "jsonb":
                _convert_pg_column(bind, table_name, column_name, "json")
