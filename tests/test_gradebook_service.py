from __future__ import annotations

from datetime import datetime, timedelta
from threading import Event, Thread
from uuid import uuid4

import pytest
from fastapi import HTTPException

from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import (
    CourseMembershipRole,
    Enrollment,
    EnrollmentStatus,
)
from fair_platform.backend.data.models.lms_gradebook import GradeCategory, GradeEntry
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.services.gradebook import (
    create_category,
    create_manual_item,
    ensure_assignment_grade_item,
    ensure_default_category,
    gradebook_projection,
    legacy_course_grading_data,
    move_item,
    sync_released_submission_entry,
    update_item,
    upsert_manual_entry,
)
from fair_platform.backend.services.submission_manager import get_submission_manager


def _fixture(session):
    owner = User(
        id=uuid4(),
        name="Owner",
        email=f"owner-{uuid4().hex[:6]}@test.com",
        role=UserRole.instructor,
        password_hash="not-used",
        is_verified=True,
    )
    student = User(
        id=uuid4(),
        name="Student",
        email=f"student-{uuid4().hex[:6]}@test.com",
        role=UserRole.student,
        password_hash="not-used",
        is_verified=True,
    )
    outsider = User(
        id=uuid4(),
        name="Outsider",
        email=f"outsider-{uuid4().hex[:6]}@test.com",
        role=UserRole.student,
        password_hash="not-used",
        is_verified=True,
    )
    course = Course(id=uuid4(), name="Gradebook", instructor_id=owner.id)
    assignment = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Essay",
        max_grade={"type": "points", "value": 100},
        status=AssignmentStatus.published,
    )
    session.add_all([owner, student, outsider, course, assignment])
    session.flush()
    session.add(Enrollment(id=uuid4(), course_id=course.id, user_id=student.id))
    submitter = Submitter(
        id=uuid4(),
        user_id=student.id,
        name=student.name,
        email=str(student.email),
        is_synthetic=False,
    )
    session.add(submitter)
    session.flush()
    return owner, student, outsider, course, assignment, submitter


def test_assignment_item_sync_and_published_only_projection(test_db):
    with test_db() as session:
        owner, student, _, course, assignment, submitter = _fixture(session)
        item = ensure_assignment_grade_item(session, assignment)
        assert item.category_id == ensure_default_category(session, course.id).id
        assert float(item.max_points) == 100

        assignment.title = "Revised essay"
        assignment.max_grade = {"type": "points", "value": 80}
        same_item = ensure_assignment_grade_item(session, assignment)
        assert same_item.id == item.id
        assert same_item.title == "Revised essay"
        assert float(same_item.max_points) == 80

        submission = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=student.id,
            submitted_at=datetime.utcnow(),
            status=SubmissionStatus.graded,
            draft_score=77,
        )
        session.add(submission)
        session.flush()

        assert sync_released_submission_entry(session, submission, owner) is None
        assert session.query(GradeEntry).count() == 0

        submission.published_score = 71
        submission.status = SubmissionStatus.returned
        submission.returned_at = datetime.utcnow()
        entry = sync_released_submission_entry(session, submission, owner)
        assert entry is not None
        assert float(entry.points_earned) == submission.published_score == 71
        assert entry.source_id == submission.id

        submission.draft_score = 99
        submission.published_score = 74
        revised = sync_released_submission_entry(session, submission, owner)
        assert revised.id == entry.id
        assert float(revised.points_earned) == submission.published_score == 74
        assert float(revised.points_earned) != submission.draft_score


@pytest.mark.parametrize(
    ("role", "status"),
    [
        (CourseMembershipRole.student, EnrollmentStatus.removed),
        (CourseMembershipRole.assistant, EnrollmentStatus.active),
    ],
)
def test_assignment_projection_requires_active_student_enrollment(
    test_db, role, status
):
    with test_db() as session:
        owner, student, _, course, assignment, submitter = _fixture(session)
        submission = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=student.id,
            submitted_at=datetime.utcnow(),
            status=SubmissionStatus.returned,
            published_score=73,
            returned_at=datetime.utcnow(),
        )
        session.add(submission)
        session.flush()
        assert sync_released_submission_entry(session, submission, owner) is not None
        assert session.query(GradeEntry).count() == 1

        enrollment = (
            session.query(Enrollment)
            .filter(
                Enrollment.course_id == course.id,
                Enrollment.user_id == student.id,
            )
            .one()
        )
        enrollment.role = role
        enrollment.status = status
        session.flush()

        assert sync_released_submission_entry(session, submission, owner) is None
        assert session.query(GradeEntry).count() == 0


def test_assignment_projection_ranks_tied_attempts_by_submission_time(test_db):
    with test_db() as session:
        owner, student, _, _, assignment, first_submitter = _fixture(session)
        second_submitter = Submitter(
            id=uuid4(),
            user_id=student.id,
            name=student.name,
            email=str(student.email),
            is_synthetic=False,
        )
        now = datetime.utcnow()
        later_submitted = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=first_submitter.id,
            created_by_id=student.id,
            submitted_at=now,
            returned_at=now + timedelta(minutes=1),
            attempt_number=1,
            status=SubmissionStatus.returned,
            published_score=88,
        )
        later_returned = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=second_submitter.id,
            created_by_id=student.id,
            submitted_at=now - timedelta(minutes=1),
            returned_at=now + timedelta(days=1),
            attempt_number=1,
            status=SubmissionStatus.returned,
            published_score=64,
        )
        session.add_all([second_submitter, later_submitted, later_returned])
        session.flush()

        entry = sync_released_submission_entry(session, later_returned, owner)
        assert entry is not None
        assert entry.source_id == later_submitted.id
        assert float(entry.points_earned) == 88


def test_manual_entries_require_active_student_and_compute_honest_totals(test_db):
    with test_db() as session:
        owner, student, outsider, course, assignment, _ = _fixture(session)
        ensure_assignment_grade_item(session, assignment)
        project_category = create_category(
            session,
            course.id,
            name="Projects",
            description=None,
            weight=60,
        )
        manual = create_manual_item(
            session,
            course.id,
            category=project_category,
            title="Presentation",
            description=None,
            max_points=20,
        )
        entry = upsert_manual_entry(
            session,
            manual,
            user_id=student.id,
            status="graded",
            points_earned=18,
            note=None,
            actor=owner,
        )
        assert float(entry.points_earned) == 18

        assignment_item = ensure_assignment_grade_item(session, assignment)
        assignment_item.position = 1_000_000
        session.flush()
        move_item(session, manual, 0)
        ordered_positions = [
            item.position
            for item in sorted(
                [manual, assignment_item], key=lambda grade_item: grade_item.position
            )
        ]
        assert ordered_positions == [0, 1]

        with pytest.raises(HTTPException, match="existing released entry"):
            update_item(session, manual, {"max_points": 17})

        with pytest.raises(HTTPException, match="maximum points"):
            upsert_manual_entry(
                session,
                manual,
                user_id=student.id,
                status="graded",
                points_earned=20.01,
                note=None,
                actor=owner,
            )

        with pytest.raises(HTTPException, match="active student"):
            upsert_manual_entry(
                session,
                manual,
                user_id=outsider.id,
                status="graded",
                points_earned=10,
                note=None,
                actor=owner,
            )

        categories, items, rows = gradebook_projection(session, course.id, [student.id])
        assert any(category["name"] == "Assignments" for category in categories)
        assert any(item["id"] == manual.id for item in items)
        total = rows[student.id]["course_total"]
        assert total["points_earned"] == 18
        assert total["points_possible"] == 20
        assert total["percentage"] == 90
        assert total["provisional"] is True
        assert total["missing_entry_count"] == 1
        assert any("not released" in reason for reason in total["reasons"])
        assert any("no configured weight" in reason for reason in total["reasons"])
        assert any("not 100" in reason for reason in total["reasons"])

        ensure_default_category(session, course.id).weight = 0
        create_category(
            session,
            course.id,
            name="Empty weighted category",
            description=None,
            weight=40,
        )
        _, _, weighted_rows = gradebook_projection(session, course.id, [student.id])
        assert any(
            "Empty weighted category has positive weight but no calculable" in reason
            for reason in weighted_rows[student.id]["course_total"]["reasons"]
        )


def test_excused_manual_entry_removes_item_from_denominator(test_db):
    with test_db() as session:
        owner, student, _, course, _, _ = _fixture(session)
        manual = create_manual_item(
            session,
            course.id,
            category=None,
            title="Participation",
            description=None,
            max_points=10,
        )
        assert manual.category_id == ensure_default_category(session, course.id).id
        upsert_manual_entry(
            session,
            manual,
            user_id=student.id,
            status="excused",
            points_earned=None,
            note="Approved accommodation",
            actor=owner,
        )
        _, _, rows = gradebook_projection(session, course.id, [student.id])
        total = rows[student.id]["course_total"]
        assert total["points_earned"] == 0
        assert total["points_possible"] == 0
        assert total["excused_item_count"] == 1
        assert total["missing_entry_count"] == 0


def test_submission_manager_rejects_invalid_scores_before_release(test_db):
    with test_db() as session:
        owner, student, _, _, assignment, submitter = _fixture(session)
        submission = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=student.id,
            submitted_at=datetime.utcnow(),
            status=SubmissionStatus.graded,
            draft_score=10,
        )
        session.add(submission)
        session.flush()
        manager = get_submission_manager(session)

        with pytest.raises(HTTPException, match="non-negative and finite"):
            manager.update_draft(submission.id, -1, None, owner)
        with pytest.raises(HTTPException, match="non-negative and finite"):
            manager.record_ai_result(submission.id, float("inf"), "bad", uuid4())

        submission.draft_score = -1
        with pytest.raises(HTTPException, match="non-negative and finite"):
            manager.return_to_student(submission.id, owner)


def test_legacy_projection_ranks_attempts_across_duplicate_submitters(test_db):
    with test_db() as session:
        _, student, _, course, assignment, first_submitter = _fixture(session)
        second_submitter = Submitter(
            id=uuid4(),
            user_id=student.id,
            name=student.name,
            email=str(student.email),
            is_synthetic=False,
        )
        older = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=first_submitter.id,
            created_by_id=student.id,
            submitted_at=datetime.utcnow(),
            attempt_number=1,
            status=SubmissionStatus.returned,
            published_score=60,
        )
        newer = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=second_submitter.id,
            created_by_id=student.id,
            submitted_at=datetime.utcnow(),
            attempt_number=2,
            status=SubmissionStatus.returned,
            published_score=80,
        )
        session.add_all([second_submitter, older, newer])
        session.flush()

        _, _, _, attempts = legacy_course_grading_data(session, course.id)
        learner_attempts = attempts[(student.id, assignment.id)]
        assert [attempt.id for attempt in learner_attempts] == [older.id, newer.id]


def test_sqlite_first_use_serializes_default_category_creation(test_db):
    with test_db() as session:
        owner = User(
            id=uuid4(),
            name="Concurrent owner",
            email=f"concurrent-{uuid4().hex[:6]}@test.com",
            role=UserRole.instructor,
            password_hash="not-used",
            is_verified=True,
        )
        course = Course(id=uuid4(), name="Concurrent course", instructor_id=owner.id)
        session.add_all([owner, course])
        session.commit()
        course_id = course.id

    first_ready = Event()
    allow_first_commit = Event()
    results: list = []
    errors: list[Exception] = []

    def create_default(wait_before_commit: bool) -> None:
        try:
            with test_db() as session:
                category = ensure_default_category(session, course_id)
                if wait_before_commit:
                    first_ready.set()
                    assert allow_first_commit.wait(5)
                session.commit()
                results.append(category.id)
        except Exception as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    first = Thread(target=create_default, args=(True,))
    second = Thread(target=create_default, args=(False,))
    first.start()
    assert first_ready.wait(5)
    second.start()
    allow_first_commit.set()
    first.join(5)
    second.join(5)

    assert not first.is_alive() and not second.is_alive()
    assert errors == []
    assert len(results) == 2
    assert results[0] == results[1]
    with test_db() as session:
        assert session.query(GradeCategory).filter_by(course_id=course_id).count() == 1
