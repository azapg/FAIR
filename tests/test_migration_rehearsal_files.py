from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path

from alembic import command
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
import pytest
from sqlalchemy import create_engine, inspect, text

from fair_platform.backend.data.migrations import (
    build_alembic_config,
    run_migrations_to_head,
    run_migrations_to_revision,
)


REHEARSAL_OLD_REVISION = "20260203_0003"
PRE_MERGE_LMS_REVISION = "20260713_0021"
PRE_MERGE_LMS_MIGRATIONS = (
    "20260714_0021_lms_course_memberships",
    "20260714_0022_lms_assignment_submissions",
    "20260714_0023_lms_communication",
    "20260714_0024_lms_submission_comments",
)


def _alembic_head() -> str:
    script = ScriptDirectory.from_config(build_alembic_config("sqlite:///:memory:"))
    return script.get_current_head()


def _read_revision(db_path: Path) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    assert row is not None
    return row[0]


def test_upgrade_rehearsal_from_old_revision_to_head(tmp_path: Path) -> None:
    db_path = tmp_path / "rehearsal_old.sqlite"
    database_url = f"sqlite:///{db_path.as_posix()}"

    run_migrations_to_revision(REHEARSAL_OLD_REVISION, database_url)
    assert _read_revision(db_path) == REHEARSAL_OLD_REVISION

    run_migrations_to_head(database_url)
    assert _read_revision(db_path) == _alembic_head()


def test_upgrade_rehearsal_head_to_head_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "rehearsal_head.sqlite"
    database_url = f"sqlite:///{db_path.as_posix()}"

    run_migrations_to_head(database_url)
    first = _read_revision(db_path)

    run_migrations_to_head(database_url)
    second = _read_revision(db_path)

    assert first == _alembic_head()
    assert second == first


def test_upgrade_rehearsal_from_pre_merge_lms_head(tmp_path: Path) -> None:
    db_path = tmp_path / "rehearsal_pre_merge_lms.sqlite"
    database_url = f"sqlite:///{db_path.as_posix()}"
    run_migrations_to_revision("20260711_0017", database_url)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        for migration_name in PRE_MERGE_LMS_MIGRATIONS:
            migration = importlib.import_module(
                "fair_platform.backend.alembic.versions." + migration_name
            )
            original_op = migration.op
            migration.op = operations
            try:
                migration.upgrade()
            finally:
                migration.op = original_op
        connection.execute(
            text("UPDATE alembic_version SET version_num = :revision"),
            {"revision": PRE_MERGE_LMS_REVISION},
        )
    engine.dispose()

    run_migrations_to_head(database_url)

    engine = create_engine(database_url)
    with engine.connect() as connection:
        schema = inspect(connection)
        tables = set(schema.get_table_names())
        execution_columns = {
            column["name"] for column in schema.get_columns("executions")
        }
        assert _read_revision(db_path) == _alembic_head()
        assert {"course_posts", "submission_comments"} <= tables
        assert {"course_id", "assignment_id"} <= execution_columns
        assert "workflows" not in tables
        assert "workflow_runs" not in tables
    engine.dispose()


def test_destructive_cutover_rejects_downgrade(tmp_path: Path) -> None:
    db_path = tmp_path / "rehearsal_destructive_cutover.sqlite"
    database_url = f"sqlite:///{db_path.as_posix()}"

    run_migrations_to_head(database_url)
    with pytest.raises(RuntimeError, match="intentional destructive cutover"):
        command.downgrade(build_alembic_config(database_url), "20260307_0013")
    assert _read_revision(db_path) == _alembic_head()


def test_build_alembic_config_skips_runtime_logging_reconfiguration() -> None:
    config = build_alembic_config("sqlite:///:memory:")
    assert config.get_main_option("fair.skip_logging_config") == "1"


def test_phase1_revision_is_explicit_and_not_live_metadata_driven() -> None:
    revision = (
        Path(__file__).parents[1]
        / "src/fair_platform/backend/alembic/versions/20260711_0017_phase1_foundation.py"
    ).read_text(encoding="utf-8")
    assert "Base.metadata.create_all" not in revision
    assert 'op.create_table(\n        "executions"' in revision
    assert 'op.create_table(\n        "artifact_versions"' in revision
    assert 'op.create_table(\n        "flow_versions"' in revision
