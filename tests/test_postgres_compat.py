from __future__ import annotations

import importlib.util
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
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
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submission_event import (
    SubmissionEvent,
    SubmissionEventType,
)
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User
from fair_platform.backend.services.execution_store import (
    ExecutionStoreError,
    append_execution_event,
    create_execution,
)
from fair_platform.backend.services.execution_projection import append_and_project_event
from fair_platform.backend.data.models.execution import Execution, ExecutionEvent


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
    test_url_str = test_url.render_as_string(hide_password=False)

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
            run_migrations_to_head(test_url_str)
        except SQLAlchemyError as exc:
            if _is_strict_mode():
                raise
            pytest.skip(f"PostgreSQL migration rehearsal unavailable: {exc}")
        yield test_url_str
    finally:
        test_engine = create_engine(test_url, future=True)
        test_engine.dispose()

        admin_engine = create_engine(
            admin_url, isolation_level="AUTOCOMMIT", future=True
        )
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
        ("users", "settings"),
        ("flow_versions", "definition"),
        ("flow_versions", "capability_pins"),
        ("executions", "input"),
        ("execution_events", "payload"),
        ("extension_installations", "manifest"),
        ("capability_definitions", "tool_capabilities"),
        ("artifact_versions", "provenance"),
        ("submission_events", "details"),
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


def test_postgres_serializes_competing_terminal_outcomes(
    postgres_database_url: str,
) -> None:
    """The Execution row lock permits exactly one terminal outcome."""

    engine = create_engine(postgres_database_url, future=True)
    with Session(engine) as session:
        user = User(
            id=uuid.uuid4(),
            name="Terminal Race User",
            email=f"terminal-race-{uuid.uuid4()}@example.test",
            role="admin",
            password_hash=None,
        )
        session.add(user)
        session.flush()
        execution = create_execution(
            session,
            kind="agent",
            initiated_by_user_id=user.id,
        )
        execution_id = execution.id
        session.commit()

    def terminate(event_type: str) -> str:
        with Session(engine) as session:
            try:
                append_and_project_event(
                    session,
                    execution_id=execution_id,
                    producer_source="postgres-race",
                    producer_event_id=event_type,
                    event_type=event_type,
                    schema_uri=f"urn:fair:event:{event_type}:v1",
                    payload={},
                )
                session.commit()
                return "accepted"
            except ExecutionStoreError:
                session.rollback()
                return "rejected"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(
            pool.map(terminate, ("execution.completed", "execution.failed"))
        )
    assert sorted(outcomes) == ["accepted", "rejected"]

    with Session(engine) as session:
        execution = session.get(Execution, execution_id)
        events = list(
            session.query(ExecutionEvent).filter(
                ExecutionEvent.execution_id == execution_id
            )
        )
        assert execution.status in {"completed", "failed"}
        assert len(events) == 1
        assert events[0].type == f"execution.{execution.status}"
    engine.dispose()


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
            draft_score=None,
            draft_feedback=None,
            published_score=None,
            published_feedback=None,
            returned_at=None,
        )
        session.add(submission)
        session.flush()

        execution = create_execution(
            session,
            kind="capability",
            initiated_by_user_id=user.id,
            course_id=course.id,
            assignment_id=assignment.id,
            submission_ids=[submission.id],
            input={"source": "postgres-compat"},
        )
        append_execution_event(
            session,
            execution_id=execution.id,
            producer_source="postgres-compat",
            producer_event_id="event-1",
            event_type="execution.started",
            schema_uri="urn:fair:event:execution.started:v1",
            payload={"status": "running"},
        )

        event = SubmissionEvent(
            id=uuid.uuid4(),
            submission_id=submission.id,
            event_type=SubmissionEventType.submission_submitted,
            actor_id=user.id,
            execution_id=execution.id,
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
