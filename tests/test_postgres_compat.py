from __future__ import annotations

import importlib.util
import os
import uuid
from datetime import datetime
from typing import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from fair_platform.backend.data.migrations import run_migrations_to_head
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.plugin import Plugin
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submission_event import (
    SubmissionEvent,
    SubmissionEventType,
)
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User
from fair_platform.backend.data.models.workflow import Workflow


def _normalize_postgres_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return "postgresql+psycopg://" + raw_url[len("postgres://") :]
    if raw_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + raw_url[len("postgresql://") :]
    return raw_url


def _require_postgres_test_url() -> str:
    if importlib.util.find_spec("psycopg") is None:
        pytest.skip("psycopg is required for PostgreSQL integration tests")
    raw = os.getenv("POSTGRES_TEST_URL", "").strip()
    if not raw:
        pytest.skip("POSTGRES_TEST_URL is not configured")
    normalized = _normalize_postgres_url(raw)
    if not normalized.startswith("postgresql+psycopg://"):
        pytest.skip("POSTGRES_TEST_URL must be a PostgreSQL URL")
    return normalized


def _is_strict_mode() -> bool:
    raw = os.getenv("POSTGRES_TEST_STRICT", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


@pytest.fixture(scope="module")
def postgres_database_url() -> Iterator[str]:
    admin_url = make_url(_require_postgres_test_url())
    db_name = f"fair_test_{uuid.uuid4().hex[:10]}"
    test_url: URL = admin_url.set(database=db_name)

    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
    try:
        with admin_engine.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    except SQLAlchemyError as exc:
        admin_engine.dispose()
        if _is_strict_mode():
            raise
        pytest.skip(f"PostgreSQL integration unavailable: {exc}")
    admin_engine.dispose()

    try:
        try:
            run_migrations_to_head(str(test_url))
        except SQLAlchemyError as exc:
            if _is_strict_mode():
                raise
            pytest.skip(f"PostgreSQL migration rehearsal unavailable: {exc}")
        yield str(test_url)
    finally:
        test_engine = create_engine(test_url, future=True)
        test_engine.dispose()

        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT", future=True)
        with admin_engine.connect() as conn:
            conn.execute(
                text(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = :db_name
                      AND pid <> pg_backend_pid()
                    """
                ),
                {"db_name": db_name},
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin_engine.dispose()


def test_postgres_json_columns_are_jsonb(postgres_database_url: str) -> None:
    engine = create_engine(postgres_database_url, future=True)
    columns = [
        ("assignments", "max_grade"),
        ("artifacts", "meta"),
        ("plugins", "meta"),
        ("plugins", "settings_schema"),
        ("users", "settings"),
        ("workflows", "transcriber_settings"),
        ("workflows", "grader_settings"),
        ("workflows", "validator_settings"),
        ("workflow_runs", "logs"),
        ("submission_events", "details"),
        ("submission_results", "grading_meta"),
        ("rubrics", "content"),
    ]

    with engine.connect() as conn:
        for table_name, column_name in columns:
            row = conn.execute(
                text(
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
            assert row is not None
            assert row[0] == "jsonb"

    engine.dispose()


def test_plugins_primary_key_is_hash(postgres_database_url: str) -> None:
    engine = create_engine(postgres_database_url, future=True)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT a.attname
                FROM pg_index i
                JOIN pg_class t ON t.oid = i.indrelid
                JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(i.indkey)
                WHERE t.relname = 'plugins'
                  AND i.indisprimary
                ORDER BY a.attnum
                """
            )
        ).all()
    engine.dispose()

    assert [r[0] for r in rows] == ["hash"]


def test_postgres_fk_and_cascade_behavior(postgres_database_url: str) -> None:
    engine = create_engine(postgres_database_url, future=True)
    with Session(engine) as session:
        user = User(
            id=uuid.uuid4(),
            name="PG User",
            email="pg-user@example.com",
            role="admin",
            password_hash=None,
            settings={"theme": "system"},
        )
        session.add(user)
        session.flush()

        course = Course(
            id=uuid.uuid4(),
            name="PG Course",
            description="Postgres integration",
            instructor_id=user.id,
            enrollment_code="PGCODE1",
            is_enrollment_enabled=True,
        )
        session.add(course)
        session.flush()

        plugin = Plugin(
            hash="plugin-hash-1",
            id="plugin-id",
            name="Plugin",
            description=None,
            author="FAIR",
            author_email=None,
            version="1.0.0",
            source="local",
            meta={"k": "v"},
            type="grader",
            settings_schema={"type": "object"},
        )
        session.add(plugin)
        session.flush()

        workflow = Workflow(
            id=uuid.uuid4(),
            course_id=course.id,
            name="Workflow",
            description=None,
            created_by=user.id,
            created_at=datetime.utcnow(),
            updated_at=None,
            archived=False,
            transcriber_plugin_hash=plugin.hash,
            transcriber_settings={"a": 1},
            grader_plugin_hash=plugin.hash,
            grader_settings={"b": 2},
            validator_plugin_hash=plugin.hash,
            validator_settings={"c": 3},
        )
        session.add(workflow)
        session.flush()

        assignment = Assignment(
            id=uuid.uuid4(),
            course_id=course.id,
            title="A1",
            description=None,
            deadline=None,
            max_grade={"value": 100},
        )
        session.add(assignment)
        session.flush()

        submitter = Submitter(
            id=uuid.uuid4(),
            name="Student",
            email="student@example.com",
            user_id=user.id,
            is_synthetic=False,
        )
        session.add(submitter)
        session.flush()

        submission = Submission(
            id=uuid.uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=user.id,
            submitted_at=datetime.utcnow(),
            status=SubmissionStatus.submitted,
            official_run_id=None,
            draft_score=None,
            draft_feedback=None,
            published_score=None,
            published_feedback=None,
            returned_at=None,
        )
        session.add(submission)
        session.flush()

        event = SubmissionEvent(
            id=uuid.uuid4(),
            submission_id=submission.id,
            event_type=SubmissionEventType.submission_submitted,
            actor_id=user.id,
            workflow_run_id=None,
            details={"status": "submitted"},
            created_at=datetime.utcnow(),
        )
        session.add(event)
        session.commit()

        session.delete(submission)
        session.commit()

        remaining = (
            session.query(SubmissionEvent)
            .filter(SubmissionEvent.id == event.id)
            .count()
        )
        assert remaining == 0

    engine.dispose()
