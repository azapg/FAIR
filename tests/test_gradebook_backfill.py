from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import sqlalchemy as sa
import pytest
from alembic import command
from sqlalchemy import create_engine

from fair_platform.backend.data.database import Base
from fair_platform.backend.data.migrations import (
    build_alembic_config,
    run_migrations_to_revision,
)
import fair_platform.backend.data.models  # noqa: F401
import fair_platform.backend.data.models.lms_gradebook  # noqa: F401


A1_REVISION = "20260812_0030"
A3_REVISION = "20260812_0031"


def _seed_legacy_grade_data(database_url: str) -> dict[str, UUID]:
    engine = create_engine(database_url)
    users = Base.metadata.tables["users"]
    courses = Base.metadata.tables["courses"]
    enrollments = Base.metadata.tables["enrollments"]
    assignments = Base.metadata.tables["assignments"]
    submitters = Base.metadata.tables["submitters"]
    submissions = Base.metadata.tables["submissions"]
    now = datetime.now(timezone.utc)
    owner_id = uuid4()
    student_id = uuid4()
    course_id = uuid4()
    returned_assignment_id = uuid4()
    excused_assignment_id = uuid4()
    draft_only_assignment_id = uuid4()
    submitter_id = uuid4()
    latest_returned_id = uuid4()

    with engine.begin() as connection:
        for user_id, name, role in (
            (owner_id, "Backfill Owner", "instructor"),
            (student_id, "Backfill Student", "student"),
        ):
            connection.execute(
                users.insert().values(
                    id=user_id,
                    name=name,
                    email=f"{name.lower().replace(' ', '-')}-{uuid4()}@example.test",
                    role=role,
                    password_hash=None,
                    is_verified=True,
                    settings={},
                )
            )
        connection.execute(
            courses.insert().values(
                id=course_id,
                name="Legacy Gradebook",
                description=None,
                instructor_id=owner_id,
                enrollment_code=None,
                is_enrollment_enabled=True,
                section=None,
                term=None,
                is_archived=False,
                created_at=now,
                updated_at=now,
            )
        )
        for user_id, role in ((owner_id, "owner"), (student_id, "student")):
            connection.execute(
                enrollments.insert().values(
                    id=uuid4(),
                    user_id=user_id,
                    course_id=course_id,
                    enrolled_at=now,
                    role=role,
                    status="active",
                    updated_at=now,
                )
            )
        for assignment_id, title, max_points in (
            (returned_assignment_id, "Returned essay", 100),
            (excused_assignment_id, "Excused presentation", 20),
            (draft_only_assignment_id, "Unreleased quiz", 10),
        ):
            connection.execute(
                assignments.insert().values(
                    id=assignment_id,
                    course_id=course_id,
                    title=title,
                    description=None,
                    deadline=None,
                    max_grade={"type": "points", "value": max_points},
                    status="published",
                    published_at=now,
                    allow_resubmissions=True,
                )
            )
        connection.execute(
            submitters.insert().values(
                id=submitter_id,
                name="Backfill Student",
                email="backfill-student@example.test",
                user_id=student_id,
                is_synthetic=False,
                created_at=now,
            )
        )

        def insert_submission(
            *,
            submission_id: UUID,
            assignment_id: UUID,
            status: str,
            attempt: int,
            draft_score: float | None,
            published_score: float | None,
        ) -> None:
            connection.execute(
                submissions.insert().values(
                    id=submission_id,
                    assignment_id=assignment_id,
                    submitter_id=submitter_id,
                    created_by_id=student_id,
                    submitted_at=now + timedelta(minutes=attempt),
                    status=status,
                    draft_score=draft_score,
                    draft_feedback=None,
                    published_score=published_score,
                    published_feedback=None,
                    returned_at=(
                        now + timedelta(minutes=attempt)
                        if status in {"returned", "excused"}
                        else None
                    ),
                    attempt_number=attempt,
                    is_late=False,
                )
            )

        insert_submission(
            submission_id=uuid4(),
            assignment_id=returned_assignment_id,
            status="returned",
            attempt=1,
            draft_score=99,
            published_score=60,
        )
        insert_submission(
            submission_id=latest_returned_id,
            assignment_id=returned_assignment_id,
            status="returned",
            attempt=2,
            draft_score=100,
            published_score=85,
        )
        insert_submission(
            submission_id=uuid4(),
            assignment_id=excused_assignment_id,
            status="excused",
            attempt=1,
            draft_score=20,
            published_score=None,
        )
        insert_submission(
            submission_id=uuid4(),
            assignment_id=draft_only_assignment_id,
            status="returned",
            attempt=1,
            draft_score=9,
            published_score=8,
        )
        insert_submission(
            submission_id=uuid4(),
            assignment_id=draft_only_assignment_id,
            status="graded",
            attempt=2,
            draft_score=10,
            published_score=None,
        )
    engine.dispose()
    return {
        "course_id": course_id,
        "student_id": student_id,
        "returned_assignment_id": returned_assignment_id,
        "latest_returned_id": latest_returned_id,
    }


def _gradebook_rows(database_url: str) -> tuple[list[dict], list[dict], list[dict]]:
    engine = create_engine(database_url)
    categories = Base.metadata.tables["grade_categories"]
    items = Base.metadata.tables["grade_items"]
    entries = Base.metadata.tables["grade_entries"]
    with engine.connect() as connection:
        category_rows = list(connection.execute(sa.select(categories)).mappings())
        item_rows = list(
            connection.execute(sa.select(items).order_by(items.c.title)).mappings()
        )
        entry_rows = list(
            connection.execute(sa.select(entries).order_by(entries.c.status)).mappings()
        )
    engine.dispose()
    return category_rows, item_rows, entry_rows


def test_gradebook_backfill_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'gradebook-backfill.sqlite').as_posix()}"
    run_migrations_to_revision(A1_REVISION, database_url)
    seeded = _seed_legacy_grade_data(database_url)

    run_migrations_to_revision(A3_REVISION, database_url)
    categories, items, entries = _gradebook_rows(database_url)
    assert len(categories) == 1
    assert categories[0]["course_id"] == seeded["course_id"]
    assert categories[0]["calculation_policy"]["fairDefaultCategory"] == "assignments"
    assert len(items) == 3
    assert all(item["category_id"] == categories[0]["id"] for item in items)
    assert all(item["source_type"] == "assignment" for item in items)
    assert len(entries) == 2

    graded = next(entry for entry in entries if entry["status"] == "graded")
    assert graded["user_id"] == seeded["student_id"]
    assert float(graded["points_earned"]) == 85
    assert graded["source_id"] == seeded["latest_returned_id"]
    assert graded["source_version"].startswith("fair-gradebook-backfill-20260812_0031:")
    excused = next(entry for entry in entries if entry["status"] == "excused")
    assert excused["points_earned"] is None

    command.downgrade(build_alembic_config(database_url), A1_REVISION)
    categories, items, entries = _gradebook_rows(database_url)
    assert categories == []
    assert items == []
    assert entries == []

    run_migrations_to_revision(A3_REVISION, database_url)
    categories, items, entries = _gradebook_rows(database_url)
    assert len(categories) == 1
    assert len(items) == 3
    assert len(entries) == 2


def test_gradebook_backfill_rejects_invalid_published_scores(tmp_path: Path) -> None:
    database_url = f"sqlite:///{(tmp_path / 'gradebook-invalid.sqlite').as_posix()}"
    run_migrations_to_revision(A1_REVISION, database_url)
    seeded = _seed_legacy_grade_data(database_url)
    engine = create_engine(database_url)
    submissions = Base.metadata.tables["submissions"]
    with engine.begin() as connection:
        connection.execute(
            submissions.update()
            .where(submissions.c.id == seeded["latest_returned_id"])
            .values(published_score=-1)
        )
    engine.dispose()

    with pytest.raises(ValueError, match=str(seeded["latest_returned_id"])):
        run_migrations_to_revision(A3_REVISION, database_url)


def test_gradebook_backfill_rejects_existing_entry_parity_mismatch(
    tmp_path: Path,
) -> None:
    database_url = f"sqlite:///{(tmp_path / 'gradebook-parity.sqlite').as_posix()}"
    run_migrations_to_revision(A1_REVISION, database_url)
    seeded = _seed_legacy_grade_data(database_url)
    engine = create_engine(database_url)
    items = Base.metadata.tables["grade_items"]
    entries = Base.metadata.tables["grade_entries"]
    item_id = uuid4()
    entry_id = uuid4()
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            items.insert().values(
                id=item_id,
                course_id=seeded["course_id"],
                category_id=None,
                title="Existing assignment projection",
                description=None,
                position=0,
                max_points=100,
                weight=None,
                calculation_policy={},
                release_policy={},
                source_type="assignment",
                source_id=seeded["returned_assignment_id"],
                copied_from_id=None,
                created_at=now,
                updated_at=now,
            )
        )
        connection.execute(
            entries.insert().values(
                id=entry_id,
                course_id=seeded["course_id"],
                grade_item_id=item_id,
                user_id=seeded["student_id"],
                status="graded",
                points_earned=84,
                release_state="released",
                released_at=now,
                graded_at=now,
                source_type="submission",
                source_id=seeded["latest_returned_id"],
                source_version="p0-existing",
                recorded_by_user_id=None,
                note=None,
                created_at=now,
                updated_at=now,
            )
        )
    engine.dispose()

    with pytest.raises(ValueError, match=str(entry_id)):
        run_migrations_to_revision(A3_REVISION, database_url)
