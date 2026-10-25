from datetime import datetime, timedelta
from importlib import import_module
from uuid import UUID, uuid4

import pytest
from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import select

from fair_platform.backend.data.models.lms_gradebook import GradeEntry, GradeItem
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.migrations import run_migrations_to_revision
from fair_platform.backend.services.gradebook import sync_released_submission_entry
from tests.test_gradebook_service import _fixture

repair = import_module(
    "fair_platform.backend.alembic.versions.20261025_0037_clear_resubmitted_grades"
)


@pytest.mark.parametrize(
    "case,removed",
    [
        ("submitted", True),
        ("private_draft", True),
        ("returned_without_points", True),
        ("tied_number", True),
        ("tied_time", True),
        ("duplicate_submitter", True),
        ("older_attempt", False),
        ("latest_returned", False),
        ("latest_excused", False),
        ("synthetic", False),
        ("unreleased_entry", False),
        ("other_source", False),
        ("manual_item", False),
        ("quiz_item", False),
        ("removed_learner", False),
    ],
)
def test_repair_only_removes_confirmed_obsolete_released_entries(
    test_db, case, removed
):
    with test_db() as session:
        owner, student, _, _, assignment, submitter = _fixture(session)
        now = datetime.utcnow()
        old = Submission(
            id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-000000000001"),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=student.id,
            attempt_number=2,
            submitted_at=now,
            status=SubmissionStatus.returned,
            published_score=80,
            published_feedback="Keep the historical feedback",
        )
        session.add(old)
        session.flush()
        entry = sync_released_submission_entry(session, old, owner)
        entry_id = entry.id
        newer = Submission(
            id=UUID("aaaaaaaa-aaaa-aaaa-aaaa-000000000002"),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=student.id,
            attempt_number=3,
            submitted_at=now + timedelta(seconds=1),
            status=SubmissionStatus.submitted,
        )
        if case == "private_draft":
            newer.status = SubmissionStatus.graded
            newer.draft_score = 95
            newer.draft_feedback = "Keep private"
        if case == "returned_without_points":
            newer.status = SubmissionStatus.returned
        if case == "tied_number":
            newer.attempt_number = old.attempt_number
        if case == "tied_time":
            newer.attempt_number = old.attempt_number
            newer.submitted_at = old.submitted_at
        if case == "older_attempt":
            newer.attempt_number = 1
        if case == "latest_returned":
            newer.status = SubmissionStatus.returned
            newer.published_score = 95
        if case == "latest_excused":
            newer.status = SubmissionStatus.excused
        if case in {"synthetic", "duplicate_submitter"}:
            duplicate = Submitter(
                id=uuid4(),
                name="Other submitter",
                user_id=student.id,
                is_synthetic=case == "synthetic",
            )
            session.add(duplicate)
            session.flush()
            newer.submitter_id = duplicate.id
        if case == "unreleased_entry":
            entry.release_state = "unreleased"
            entry.released_at = None
        if case == "other_source":
            entry.source_type = "manual"
        if case in {"manual_item", "quiz_item"}:
            item = session.get(GradeItem, entry.grade_item_id)
            item.source_type = "manual" if case == "manual_item" else "quiz"
        if case == "removed_learner":
            from fair_platform.backend.data.models.enrollment import Enrollment

            session.query(Enrollment).filter_by(
                user_id=student.id
            ).one().status = "removed"
        session.add(newer)
        session.commit()
        # If the latest attempt is validly released, retain its canonical entry.
        if case in {"latest_returned", "latest_excused"}:
            sync_released_submission_entry(session, newer, owner)
            session.commit()
        before_entries = session.execute(select(GradeEntry.__table__)).mappings().all()
        before_submissions = (
            session.execute(select(Submission.__table__)).mappings().all()
        )

    with test_db() as session, session.get_bind().begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            repair.upgrade()
            repair.downgrade()
            repair.upgrade()  # Safe to rerun; downgrade never revives bad evidence.

    with test_db() as session:
        after_entries = session.execute(select(GradeEntry.__table__)).mappings().all()
        assert after_entries == ([] if removed else before_entries)
        assert (
            session.execute(select(Submission.__table__)).mappings().all()
            == before_submissions
        )
        assert (session.get(GradeEntry, entry_id) is None) == removed


def test_repair_revision_upgrades_an_existing_database(tmp_path):
    database_url = f"sqlite:///{tmp_path / 'repair.sqlite'}"
    run_migrations_to_revision("20260830_0036", database_url=database_url)
    run_migrations_to_revision(repair.revision, database_url=database_url)
