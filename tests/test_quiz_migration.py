from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from alembic import command
from sqlalchemy import UUID as SAUUID
from sqlalchemy import MetaData, create_engine, inspect, select

from fair_platform.backend.data.migrations import (
    build_alembic_config,
    run_migrations_to_head,
    run_migrations_to_revision,
)


A3_REVISION = "20260812_0031"
A4_REVISION = "20260812_0032"
QUIZ_TABLES = {
    "question_banks",
    "questions",
    "question_versions",
    "quizzes",
    "quiz_questions",
    "quiz_attempts",
    "quiz_attempt_questions",
    "quiz_answers",
}


def _revision(path: Path) -> str:
    with sqlite3.connect(path) as connection:
        row = connection.execute(
            "SELECT version_num FROM alembic_version LIMIT 1"
        ).fetchone()
    assert row is not None
    return row[0]


def test_quiz_migration_upgrades_downgrades_and_reupgrades(tmp_path: Path) -> None:
    path = tmp_path / "quiz.sqlite"
    database_url = f"sqlite:///{path.as_posix()}"
    run_migrations_to_revision(A3_REVISION, database_url)
    assert _revision(path) == A3_REVISION

    engine = create_engine(database_url)
    assert QUIZ_TABLES.isdisjoint(inspect(engine).get_table_names())
    engine.dispose()

    run_migrations_to_revision(A4_REVISION, database_url)
    assert _revision(path) == A4_REVISION
    engine = create_engine(database_url)
    schema = inspect(engine)
    assert QUIZ_TABLES <= set(schema.get_table_names())
    assert {column["name"] for column in schema.get_columns("question_versions")} >= {
        "options",
        "correct_option_id",
        "version_number",
    }
    assert {column["name"] for column in schema.get_columns("quiz_attempts")} >= {
        "earned_points",
        "released_at",
        "attempt_number",
    }
    engine.dispose()

    command.downgrade(build_alembic_config(database_url), A3_REVISION)
    assert _revision(path) == A3_REVISION
    engine = create_engine(database_url)
    assert QUIZ_TABLES.isdisjoint(inspect(engine).get_table_names())
    engine.dispose()

    run_migrations_to_head(database_url)
    assert _revision(path) == A4_REVISION


def test_populated_quiz_downgrade_removes_only_a4_generic_projections(
    tmp_path: Path,
) -> None:
    path = tmp_path / "populated-quiz.sqlite"
    database_url = f"sqlite:///{path.as_posix()}"
    run_migrations_to_revision(A4_REVISION, database_url)
    engine = create_engine(database_url)
    metadata = MetaData()
    metadata.reflect(
        engine,
        only=[
            "users",
            "courses",
            "enrollments",
            "course_sections",
            "course_items",
            "grade_items",
            "grade_entries",
            "quizzes",
            "quiz_attempts",
        ],
    )
    tables = metadata.tables
    # SQLite reflects the repository's UUID spelling as NUMERIC. Restore the
    # intended bind/result type so the rehearsal exercises UUID-shaped data
    # instead of failing in the reflected numeric processor.
    for table in tables.values():
        for column in table.columns:
            if column.name == "id" or column.name.endswith("_id"):
                column.type = SAUUID()
    now = datetime.now(timezone.utc)
    user_id = uuid4()
    course_id = uuid4()
    enrollment_id = uuid4()
    section_id = uuid4()
    quiz_id = uuid4()
    attempt_id = uuid4()
    quiz_item_id = uuid4()
    heading_id = uuid4()
    quiz_grade_item_id = uuid4()
    manual_grade_item_id = uuid4()
    quiz_entry_id = uuid4()
    manual_entry_id = uuid4()

    with engine.begin() as connection:
        connection.execute(
            tables["users"].insert(),
            {
                "id": user_id,
                "name": "Migration learner",
                "email": "migration-learner@example.com",
                "role": "user",
                "password_hash": None,
                "is_verified": True,
                "settings": {},
            },
        )
        connection.execute(
            tables["courses"].insert(),
            {
                "id": course_id,
                "name": "Populated quiz course",
                "description": None,
                "instructor_id": user_id,
                "organization_id": None,
                "enrollment_code": None,
                "is_enrollment_enabled": False,
                "section": None,
                "term": None,
                "is_archived": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            tables["enrollments"].insert(),
            {
                "id": enrollment_id,
                "user_id": user_id,
                "course_id": course_id,
                "enrolled_at": now,
                "role": "student",
                "status": "active",
                "updated_at": now,
            },
        )
        connection.execute(
            tables["course_sections"].insert(),
            {
                "id": section_id,
                "course_id": course_id,
                "title": "Week one",
                "summary": None,
                "position": 0,
                "visibility": "published",
                "copied_from_id": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            tables["quizzes"].insert(),
            {
                "id": quiz_id,
                "course_id": course_id,
                "title": "Populated quiz",
                "instructions": None,
                "status": "published",
                "release_policy": "immediate",
                "attempt_limit": 1,
                "opens_at": None,
                "closes_at": None,
                "created_by_user_id": user_id,
                "published_at": now,
                "closed_at": None,
                "created_at": now,
                "updated_at": now,
            },
        )
        connection.execute(
            tables["quiz_attempts"].insert(),
            {
                "id": attempt_id,
                "course_id": course_id,
                "quiz_id": quiz_id,
                "user_id": user_id,
                "attempt_number": 1,
                "status": "released",
                "max_points": 5,
                "earned_points": 4,
                "started_at": now,
                "submitted_at": now,
                "released_at": now,
            },
        )
        connection.execute(
            tables["course_items"].insert(),
            [
                {
                    "id": quiz_item_id,
                    "course_id": course_id,
                    "section_id": section_id,
                    "title": "Populated quiz",
                    "position": 0,
                    "kind": "quiz",
                    "visibility": "published",
                    "resource_type": "quiz",
                    "resource_id": quiz_id,
                    "copied_from_id": None,
                    "payload_schema_uri": "urn:fair:lms:course-item:quiz:v1",
                    "payload": {},
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": heading_id,
                    "course_id": course_id,
                    "section_id": section_id,
                    "title": "Keep me",
                    "position": 1,
                    "kind": "heading",
                    "visibility": "published",
                    "resource_type": None,
                    "resource_id": None,
                    "copied_from_id": None,
                    "payload_schema_uri": "urn:fair:lms:course-item:heading:v1",
                    "payload": {},
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )
        connection.execute(
            tables["grade_items"].insert(),
            [
                {
                    "id": quiz_grade_item_id,
                    "course_id": course_id,
                    "category_id": None,
                    "title": "Populated quiz",
                    "description": None,
                    "position": 0,
                    "max_points": 5,
                    "weight": None,
                    "calculation_policy": {},
                    "release_policy": {},
                    "source_type": "quiz",
                    "source_id": quiz_id,
                    "copied_from_id": None,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": manual_grade_item_id,
                    "course_id": course_id,
                    "category_id": None,
                    "title": "Keep me",
                    "description": None,
                    "position": 1,
                    "max_points": 10,
                    "weight": None,
                    "calculation_policy": {},
                    "release_policy": {},
                    "source_type": "manual",
                    "source_id": manual_grade_item_id,
                    "copied_from_id": None,
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )
        connection.execute(
            tables["grade_entries"].insert(),
            [
                {
                    "id": quiz_entry_id,
                    "course_id": course_id,
                    "grade_item_id": quiz_grade_item_id,
                    "user_id": user_id,
                    "status": "graded",
                    "points_earned": 4,
                    "release_state": "released",
                    "released_at": now,
                    "graded_at": now,
                    "source_type": "quiz_attempt",
                    "source_id": attempt_id,
                    "source_version": "attempt:1",
                    "recorded_by_user_id": user_id,
                    "note": None,
                    "created_at": now,
                    "updated_at": now,
                },
                {
                    "id": manual_entry_id,
                    "course_id": course_id,
                    "grade_item_id": manual_grade_item_id,
                    "user_id": user_id,
                    "status": "graded",
                    "points_earned": 8,
                    "release_state": "released",
                    "released_at": now,
                    "graded_at": now,
                    "source_type": "manual",
                    "source_id": manual_grade_item_id,
                    "source_version": None,
                    "recorded_by_user_id": user_id,
                    "note": None,
                    "created_at": now,
                    "updated_at": now,
                },
            ],
        )

    command.downgrade(build_alembic_config(database_url), A3_REVISION)
    assert _revision(path) == A3_REVISION
    with engine.connect() as connection:
        assert connection.execute(
            select(tables["course_items"].c.id).order_by(
                tables["course_items"].c.position
            )
        ).scalars().all() == [heading_id]
        assert connection.execute(
            select(tables["grade_items"].c.id)
        ).scalars().all() == [manual_grade_item_id]
        assert connection.execute(
            select(tables["grade_entries"].c.id)
        ).scalars().all() == [manual_entry_id]
    assert QUIZ_TABLES.isdisjoint(inspect(engine).get_table_names())
    engine.dispose()

    run_migrations_to_head(database_url)
    assert _revision(path) == A4_REVISION


def test_quiz_migration_is_explicit_and_stacked_on_gradebook() -> None:
    migration = (
        Path(__file__).parents[1]
        / "src/fair_platform/backend/alembic/versions/20260812_0032_quiz_engine.py"
    ).read_text(encoding="utf-8")
    assert 'down_revision: str = "20260812_0031"' in migration
    assert "Base.metadata.create_all" not in migration
    assert 'op.create_table(\n        "question_versions"' in migration
    assert 'op.create_table(\n        "quiz_attempts"' in migration
    assert 'op.create_table(\n        "quiz_answers"' in migration
