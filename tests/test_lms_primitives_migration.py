from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import DatabaseError

from fair_platform.backend.data.database import Base
from fair_platform.backend.data.migrations import (
    build_alembic_config,
    run_migrations_to_head,
    run_migrations_to_revision,
)
import fair_platform.backend.data.models  # noqa: F401


PRIMITIVES_REVISION = "20260812_0029"
PRIOR_REVISION = "20260727_0028"
PRIMITIVE_TABLES = {
    "activity_events",
    "availability_rules",
    "calendar_events",
    "cohort_memberships",
    "cohorts",
    "completion_rules",
    "course_group_memberships",
    "course_groups",
    "course_items",
    "course_sections",
    "external_identifiers",
    "grade_categories",
    "grade_entries",
    "grade_items",
    "notification_preferences",
    "organization_memberships",
    "organizations",
    "user_item_completions",
}


def _database_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def _revision(path: Path) -> str:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT version_num FROM alembic_version LIMIT 1"
        ).fetchone()
    assert row is not None
    return row[0]


def test_primitives_revision_is_the_sole_head() -> None:
    script = ScriptDirectory.from_config(build_alembic_config("sqlite:///:memory:"))
    assert script.get_heads() == [PRIMITIVES_REVISION]


def test_upgrade_from_points_head_has_model_column_parity(tmp_path: Path) -> None:
    database_path = tmp_path / "lms-primitives.sqlite"
    database_url = _database_url(database_path)
    run_migrations_to_revision(PRIOR_REVISION, database_url)
    assert _revision(database_path) == PRIOR_REVISION

    run_migrations_to_head(database_url)
    assert _revision(database_path) == PRIMITIVES_REVISION

    engine = create_engine(database_url)
    with engine.connect() as connection:
        schema = inspect(connection)
        assert PRIMITIVE_TABLES <= set(schema.get_table_names())
        assert "organization_id" in {
            column["name"] for column in schema.get_columns("courses")
        }
        for table_name in PRIMITIVE_TABLES:
            migrated_columns = {
                column["name"] for column in schema.get_columns(table_name)
            }
            assert migrated_columns == set(Base.metadata.tables[table_name].c.keys())
    engine.dispose()


def test_activity_event_trigger_rejects_raw_update_and_delete(tmp_path: Path) -> None:
    database_path = tmp_path / "activity-events.sqlite"
    database_url = _database_url(database_path)
    run_migrations_to_head(database_url)

    engine = create_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO activity_events "
                "(id, event_type, payload, occurred_at, recorded_at) "
                "VALUES (:id, :event_type, :payload, :occurred_at, :recorded_at)"
            ),
            {
                "id": "00000000000000000000000000000001",
                "event_type": "course.created",
                "payload": "{}",
                "occurred_at": "2026-08-12 12:00:00",
                "recorded_at": "2026-08-12 12:00:00",
            },
        )

    with engine.begin() as connection:
        with pytest.raises(DatabaseError, match="append-only"):
            connection.execute(
                text("UPDATE activity_events SET event_type = 'changed'")
            )
    with engine.begin() as connection:
        with pytest.raises(DatabaseError, match="append-only"):
            connection.execute(text("DELETE FROM activity_events"))
    engine.dispose()


def test_primitives_migration_downgrades_and_reupgrades_cleanly(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "round-trip.sqlite"
    database_url = _database_url(database_path)
    config = build_alembic_config(database_url)
    run_migrations_to_head(database_url)

    command.downgrade(config, PRIOR_REVISION)
    assert _revision(database_path) == PRIOR_REVISION
    engine = create_engine(database_url)
    with engine.connect() as connection:
        schema = inspect(connection)
        assert not (PRIMITIVE_TABLES & set(schema.get_table_names()))
        assert "organization_id" not in {
            column["name"] for column in schema.get_columns("courses")
        }
    engine.dispose()

    run_migrations_to_head(database_url)
    assert _revision(database_path) == PRIMITIVES_REVISION


def test_primitives_migration_is_explicit() -> None:
    migration = (
        Path(__file__).parents[1]
        / "src/fair_platform/backend/alembic/versions/20260812_0029_lms_primitives.py"
    ).read_text(encoding="utf-8")
    assert "Base.metadata.create_all" not in migration
    assert 'op.create_table(\n        "course_sections"' in migration
    assert 'op.create_table(\n        "grade_entries"' in migration
    assert 'op.create_table(\n        "activity_events"' in migration
