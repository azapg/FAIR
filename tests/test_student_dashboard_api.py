from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.data.models.lms_communication import (
    CoursePost,
    CoursePostKind,
)
from fair_platform.backend.data.models.lms_gradebook import GradeEntry
from fair_platform.backend.data.models.lms_content import (
    CourseContentVisibility,
    CourseItem,
    CourseSection,
)
from fair_platform.backend.data.models.lms_events import (
    CalendarEvent,
    CalendarEventVisibility,
)
from fair_platform.backend.data.models.lms_progress import (
    ItemCompletionStatus,
    UserItemCompletion,
)
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.services.gradebook import (
    create_category,
    create_manual_item,
    ensure_assignment_grade_item,
    gradebook_projection,
    sync_released_submission_entry,
    upsert_manual_entry,
)
from tests.conftest import get_auth_token


def _user(session, name: str, role: UserRole) -> User:
    user = User(
        id=uuid4(),
        name=name,
        email=f"{name.lower()}-{uuid4().hex[:6]}@test.com",
        role=role,
        password_hash=hash_password("test_password_123"),
        is_verified=True,
    )
    session.add(user)
    session.flush()
    return user


def _auth(client, user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_auth_token(client, str(user.email))}"}


def _setup(session):
    owner = _user(session, "Owner", UserRole.instructor)
    assistant = _user(session, "Assistant", UserRole.instructor)
    student = _user(session, "Student", UserRole.student)
    other_student = _user(session, "Other", UserRole.student)
    course = Course(
        id=uuid4(),
        name="Biology",
        term="Fall 2026",
        instructor_id=owner.id,
    )
    session.add(course)
    session.flush()
    session.add_all(
        [
            Enrollment(id=uuid4(), course_id=course.id, user_id=owner.id, role="owner"),
            Enrollment(
                id=uuid4(),
                course_id=course.id,
                user_id=assistant.id,
                role="assistant",
            ),
            Enrollment(
                id=uuid4(), course_id=course.id, user_id=student.id, role="student"
            ),
            Enrollment(
                id=uuid4(),
                course_id=course.id,
                user_id=other_student.id,
                role="student",
            ),
        ]
    )
    released = create_manual_item(
        session,
        course.id,
        category=None,
        title="Lab notebook",
        description=None,
        max_points=20,
    )
    unreleased = create_manual_item(
        session,
        course.id,
        category=None,
        title="Private capstone",
        description=None,
        max_points=100,
    )
    upsert_manual_entry(
        session,
        released,
        user_id=student.id,
        status="graded",
        points_earned=18,
        note="Strong observations",
        actor=owner,
    )
    upsert_manual_entry(
        session,
        released,
        user_id=other_student.id,
        status="graded",
        points_earned=7,
        note="Other learner note",
        actor=owner,
    )
    # Explicitly store an unreleased fact to exercise the privacy projection.
    session.add(
        GradeEntry(
            id=uuid4(),
            course_id=course.id,
            grade_item_id=unreleased.id,
            user_id=student.id,
            status="graded",
            points_earned=99,
            release_state="unreleased",
            source_type="manual",
            source_id=unreleased.id,
            recorded_by_user_id=owner.id,
            note="Private draft note",
        )
    )
    now = datetime.now(timezone.utc)
    upcoming = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Cell diagram",
        deadline=now + timedelta(days=2),
        max_grade={"type": "points", "value": 10},
        status=AssignmentStatus.published,
        published_at=now - timedelta(days=1),
    )
    overdue = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Overdue worksheet",
        deadline=now - timedelta(days=1),
        max_grade={"type": "points", "value": 10},
        status=AssignmentStatus.published,
        published_at=now - timedelta(days=2),
    )
    hidden = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Hidden assignment",
        deadline=now - timedelta(days=3),
        max_grade={"type": "points", "value": 10},
        status=AssignmentStatus.draft,
    )
    returned = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Returned essay",
        deadline=now - timedelta(days=4),
        max_grade={"type": "points", "value": 10},
        status=AssignmentStatus.closed,
        published_at=now - timedelta(days=7),
    )
    session.add_all([upcoming, overdue, hidden, returned])
    session.flush()
    for assignment in (upcoming, overdue, hidden, returned):
        ensure_assignment_grade_item(session, assignment)
    submitter = Submitter(
        id=uuid4(),
        name=student.name,
        email=student.email,
        user_id=student.id,
        is_synthetic=False,
    )
    session.add(submitter)
    session.flush()
    returned_submission = Submission(
        id=uuid4(),
        assignment_id=returned.id,
        submitter_id=submitter.id,
        created_by_id=owner.id,
        submitted_at=now - timedelta(days=5),
        status=SubmissionStatus.returned,
        published_score=9,
        published_feedback="Clear argument",
        returned_at=now - timedelta(hours=3),
    )
    session.add(returned_submission)
    session.flush()
    sync_released_submission_entry(session, returned_submission, owner)
    session.add(
        CoursePost(
            id=uuid4(),
            course_id=course.id,
            author_id=owner.id,
            kind=CoursePostKind.announcement,
            title="Welcome to Biology",
            body="Start with the course outline.",
            created_at=now,
            updated_at=now,
        )
    )
    session.commit()
    return owner, assistant, student, other_student, course, released


def test_student_grades_match_canonical_projection_and_hide_unreleased_identity(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, other_student, course, released = _setup(session)
        canonical = gradebook_projection(session, course.id, [student.id])[2][
            student.id
        ]["course_total"]

    response = test_client.get(
        f"/api/lms/courses/{course.id}/grades", headers=_auth(test_client, student)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == {
        "pointsEarned": canonical["points_earned"],
        "pointsPossible": canonical["points_possible"],
        "percentage": canonical["percentage"],
        "provisional": canonical["provisional"],
        "gradedItemCount": canonical["graded_item_count"],
        "excusedItemCount": canonical["excused_item_count"],
        "missingEntryCount": canonical["missing_entry_count"],
        "reasons": canonical["reasons"],
        "calculation": canonical["calculation"],
        "configuredWeightTotal": canonical["configured_weight_total"],
    }
    released_cell = next(
        item for item in body["items"] if item["gradeItemId"] == str(released.id)
    )
    assert released_cell["pointsEarned"] == 18
    assert released_cell["note"] == "Strong observations"
    assert all(item.get("pointsEarned") != 7 for item in body["items"])
    assert "Other learner note" not in response.text
    private_cell = next(
        item for item in body["items"] if item["status"] == "unreleased"
    )
    assert private_cell["title"] is None
    assert private_cell["pointsEarned"] is None
    assert private_cell["note"] is None
    assert "Private capstone" not in response.text
    assert "Private draft note" not in response.text
    missing_assignment = next(
        item for item in body["items"] if item["title"] == "Cell diagram"
    )
    assert missing_assignment["status"] == "missing"
    assert missing_assignment["assignmentId"] is not None

    # The route is self-scoped; a learner cannot request another user's context.
    assert str(other_student.id) not in response.text
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/grades",
            headers=_auth(test_client, owner),
        ).status_code
        == 403
    )


def test_dashboard_is_student_only_and_filters_hidden_work(test_client, test_db):
    with test_db() as session:
        owner, assistant, student, _, course, _ = _setup(session)
        mixed_context = _user(session, "MixedContext", UserRole.student)
        staff_course = Course(
            id=uuid4(),
            name="Staff course",
            instructor_id=mixed_context.id,
            is_archived=True,
        )
        session.add(staff_course)
        session.flush()
        session.add_all(
            [
                Enrollment(
                    id=uuid4(),
                    course_id=course.id,
                    user_id=mixed_context.id,
                    role="student",
                ),
                Enrollment(
                    id=uuid4(),
                    course_id=staff_course.id,
                    user_id=mixed_context.id,
                    role="owner",
                ),
            ]
        )
        session.commit()

    response = test_client.get(
        "/api/lms/student/dashboard", headers=_auth(test_client, student)
    )
    assert response.status_code == 200
    body = response.json()
    assert [item["title"] for item in body["upcomingWork"]] == ["Cell diagram"]
    assert [item["title"] for item in body["overdueWork"]] == ["Overdue worksheet"]
    assert "Hidden assignment" not in response.text
    assert body["upcomingWork"][0]["timezoneName"] == "UTC"
    assert body["recentActivity"][0]["title"] == "Welcome to Biology"
    assert body["recentActivity"][0]["link"] == f"/courses/{course.id}/stream"
    assert body["courseProgress"][0]["currentGrade"] == 90
    assert body["returnedFeedback"][0]["assignmentTitle"] == "Returned essay"
    assert body["returnedFeedback"][0]["link"] == f"/courses/{course.id}/grades"
    assert all(source["available"] for source in body["sources"])

    for staff in (owner, assistant):
        assert (
            test_client.get(
                "/api/lms/student/dashboard", headers=_auth(test_client, staff)
            ).status_code
            == 403
        )
    assert (
        test_client.get(
            "/api/lms/student/dashboard",
            headers=_auth(test_client, mixed_context),
        ).status_code
        == 403
    )
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/grades",
            headers=_auth(test_client, mixed_context),
        ).status_code
        == 403
    )


def test_dashboard_returns_other_sources_when_progress_fails(
    test_client, test_db, monkeypatch
):
    with test_db() as session:
        _, _, student, _, _, _ = _setup(session)

    def fail_progress(*_args, **_kwargs):
        raise RuntimeError("simulated projection failure")

    monkeypatch.setattr(
        "fair_platform.backend.services.student_dashboard.progress_projection",
        fail_progress,
    )
    response = test_client.get(
        "/api/lms/student/dashboard", headers=_auth(test_client, student)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["courseProgress"] == []
    assert body["upcomingWork"][0]["title"] == "Cell diagram"
    progress_status = next(
        item for item in body["sources"] if item["source"] == "progress"
    )
    assert progress_status == {
        "source": "progress",
        "available": False,
        "message": "Progress data is temporarily unavailable",
    }


def test_dashboard_prioritizes_actionable_dated_work_before_the_limit(
    test_client, test_db
):
    with test_db() as session:
        _, _, student, _, course, _ = _setup(session)
        now = datetime.now(timezone.utc)
        undated = [
            Assignment(
                id=uuid4(),
                course_id=course.id,
                title=f"Undated practice {index:02d}",
                deadline=None,
                max_grade={"type": "points", "value": 10},
                status=AssignmentStatus.published,
                published_at=now,
            )
            for index in range(21)
        ]
        submitted_assignment = Assignment(
            id=uuid4(),
            course_id=course.id,
            title="Already submitted",
            deadline=now + timedelta(hours=1),
            max_grade={"type": "points", "value": 10},
            status=AssignmentStatus.published,
            published_at=now,
        )
        session.add_all([*undated, submitted_assignment])
        session.flush()
        submitter = session.query(Submitter).filter_by(user_id=student.id).one()
        session.add(
            Submission(
                id=uuid4(),
                assignment_id=submitted_assignment.id,
                submitter_id=submitter.id,
                created_by_id=student.id,
                submitted_at=now,
                status=SubmissionStatus.submitted,
                attempt_number=1,
            )
        )
        session.commit()

    response = test_client.get(
        "/api/lms/student/dashboard", headers=_auth(test_client, student)
    )
    assert response.status_code == 200
    upcoming = response.json()["upcomingWork"]
    assert len(upcoming) == 20
    assert upcoming[0]["title"] == "Cell diagram"
    assert all(item["state"] == "upcoming" for item in upcoming)


def test_dashboard_work_respects_private_due_override_cutoff_and_completion(
    test_client, test_db
):
    with test_db() as session:
        _, _, student, _, course, _ = _setup(session)
        now = datetime.now(timezone.utc)
        upcoming = session.query(Assignment).filter_by(title="Cell diagram").one()
        overdue = session.query(Assignment).filter_by(title="Overdue worksheet").one()
        cutoff = Assignment(
            id=uuid4(),
            course_id=course.id,
            title="Cut off quiz",
            deadline=now - timedelta(days=2),
            max_grade={"type": "points", "value": 5},
            status=AssignmentStatus.published,
            published_at=now - timedelta(days=3),
        )
        section = CourseSection(
            id=uuid4(),
            course_id=course.id,
            title="Week one",
            position=0,
            visibility=CourseContentVisibility.published,
        )
        session.add_all([cutoff, section])
        session.flush()
        item = CourseItem(
            id=uuid4(),
            course_id=course.id,
            section_id=section.id,
            title=upcoming.title,
            position=0,
            kind="assignment",
            visibility=CourseContentVisibility.published,
            resource_type="assignment",
            resource_id=upcoming.id,
            payload={},
        )
        session.add(item)
        session.flush()
        session.add_all(
            [
                UserItemCompletion(
                    id=uuid4(),
                    course_id=course.id,
                    course_item_id=item.id,
                    user_id=student.id,
                    status=ItemCompletionStatus.completed,
                    completed_at=now,
                ),
                CalendarEvent(
                    id=uuid4(),
                    course_id=course.id,
                    owner_user_id=student.id,
                    title="Extended due date",
                    starts_at=now + timedelta(days=3),
                    timezone_name="America/Panama",
                    visibility=CalendarEventVisibility.private,
                    source_type="assignment_due_override",
                    source_id=overdue.id,
                ),
                CalendarEvent(
                    id=uuid4(),
                    course_id=course.id,
                    owner_user_id=student.id,
                    title="Submission cutoff",
                    starts_at=now - timedelta(hours=1),
                    timezone_name="America/Panama",
                    visibility=CalendarEventVisibility.private,
                    source_type="assignment_cutoff",
                    source_id=cutoff.id,
                ),
            ]
        )
        session.commit()

    body = test_client.get(
        "/api/lms/student/dashboard", headers=_auth(test_client, student)
    ).json()
    assert body["overdueWork"] == []
    assert [item["title"] for item in body["upcomingWork"]] == ["Overdue worksheet"]
    assert body["upcomingWork"][0]["timezoneName"] == "America/Panama"
    assert "Cell diagram" not in str(body["upcomingWork"])
    assert "Cut off quiz" not in str(body["upcomingWork"])
    assert body["courseProgress"][0]["completedItems"] == 1
    assert body["courseProgress"][0]["trackedItems"] == 1


def test_dashboard_supports_duplicate_submitters_and_uses_canonical_latest_attempt(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, _, course, _ = _setup(session)
        assignment = session.query(Assignment).filter_by(title="Returned essay").one()
        duplicate = Submitter(
            id=uuid4(),
            name=student.name,
            email=student.email,
            user_id=student.id,
            is_synthetic=False,
        )
        session.add(duplicate)
        session.flush()
        latest = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=duplicate.id,
            created_by_id=owner.id,
            attempt_number=2,
            submitted_at=datetime.now(timezone.utc) - timedelta(hours=2),
            status=SubmissionStatus.returned,
            published_score=8,
            published_feedback="Latest attempt feedback",
            returned_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        session.add(latest)
        session.flush()
        sync_released_submission_entry(session, latest, owner)
        session.commit()

    grades = test_client.get(
        f"/api/lms/courses/{course.id}/grades", headers=_auth(test_client, student)
    )
    assert grades.status_code == 200
    returned_grade = next(
        item for item in grades.json()["items"] if item["submissionId"] is not None
    )
    assert returned_grade["submissionId"] == str(latest.id)

    dashboard = test_client.get(
        "/api/lms/student/dashboard", headers=_auth(test_client, student)
    )
    assert dashboard.status_code == 200
    feedback = dashboard.json()["returnedFeedback"]
    assert feedback[0]["submissionId"] == str(latest.id)
    assert feedback[0]["pointsEarned"] == 8


def test_dashboard_ignores_private_timing_event_from_another_course(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, _, first_course, _ = _setup(session)
        second_course = Course(id=uuid4(), name="Chemistry", instructor_id=owner.id)
        session.add(second_course)
        session.flush()
        session.add(
            Enrollment(
                id=uuid4(),
                course_id=second_course.id,
                user_id=student.id,
                role="student",
            )
        )
        foreign_assignment = Assignment(
            id=uuid4(),
            course_id=second_course.id,
            title="Chemistry overdue",
            deadline=datetime.now(timezone.utc) - timedelta(days=1),
            max_grade={"type": "points", "value": 5},
            status=AssignmentStatus.published,
            published_at=datetime.now(timezone.utc) - timedelta(days=2),
        )
        session.add(foreign_assignment)
        session.flush()
        session.add(
            CalendarEvent(
                id=uuid4(),
                course_id=first_course.id,
                owner_user_id=student.id,
                title="Wrong-course cutoff",
                starts_at=datetime.now(timezone.utc) - timedelta(hours=1),
                timezone_name="America/Panama",
                visibility=CalendarEventVisibility.private,
                source_type="assignment_cutoff",
                source_id=foreign_assignment.id,
            )
        )
        session.commit()

    response = test_client.get(
        "/api/lms/student/dashboard", headers=_auth(test_client, student)
    )
    assert response.status_code == 200
    assert "Chemistry overdue" in [
        item["title"] for item in response.json()["overdueWork"]
    ]


def test_weighted_item_contributions_sum_to_canonical_current_grade_and_final_is_explicit(
    test_client, test_db
):
    with test_db() as session:
        owner = _user(session, "WeightedOwner", UserRole.instructor)
        student = _user(session, "WeightedStudent", UserRole.student)
        course = Course(id=uuid4(), name="Weighted course", instructor_id=owner.id)
        session.add(course)
        session.flush()
        session.add_all(
            [
                Enrollment(
                    id=uuid4(), course_id=course.id, user_id=owner.id, role="owner"
                ),
                Enrollment(
                    id=uuid4(),
                    course_id=course.id,
                    user_id=student.id,
                    role="student",
                ),
            ]
        )
        first_category = create_category(
            session,
            course.id,
            name="Practice",
            description=None,
            weight=25,
        )
        second_category = create_category(
            session,
            course.id,
            name="Projects",
            description=None,
            weight=75,
        )
        first_item = create_manual_item(
            session,
            course.id,
            category=first_category,
            title="Practice one",
            description=None,
            max_points=10,
        )
        second_item = create_manual_item(
            session,
            course.id,
            category=second_category,
            title="Project one",
            description=None,
            max_points=20,
        )
        upsert_manual_entry(
            session,
            first_item,
            user_id=student.id,
            status="graded",
            points_earned=5,
            note=None,
            actor=owner,
        )
        upsert_manual_entry(
            session,
            second_item,
            user_id=student.id,
            status="graded",
            points_earned=20,
            note=None,
            actor=owner,
        )
        session.commit()

    response = test_client.get(
        f"/api/lms/courses/{course.id}/grades", headers=_auth(test_client, student)
    )
    body = response.json()
    assert response.status_code == 200
    assert body["total"]["percentage"] == 87.5
    assert sum(item["contributionPercentagePoints"] for item in body["items"]) == 87.5
    assert body["currentGradeLabel"] == "Current grade"
    assert body["finalGradeAvailable"] is False

    with test_db() as session:
        session.get(Course, course.id).is_archived = True
        session.commit()
    archived = test_client.get(
        f"/api/lms/courses/{course.id}/grades", headers=_auth(test_client, student)
    ).json()
    assert archived["currentGradeLabel"] == "Final grade"
    assert archived["finalGradeAvailable"] is True


def test_student_endpoints_are_registered_as_self_scoped_openapi_operations(
    test_client,
):
    schema = test_client.app.openapi()
    dashboard = schema["paths"]["/api/lms/student/dashboard"]["get"]
    grades = schema["paths"]["/api/lms/courses/{course_id}/grades"]["get"]
    assert dashboard["tags"] == ["student-dashboard"]
    assert grades["tags"] == ["student-dashboard"]
    assert dashboard["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/StudentDashboard")
    assert grades["responses"]["200"]["content"]["application/json"]["schema"][
        "$ref"
    ].endswith("/StudentCourseGrades")
    assert [parameter["name"] for parameter in grades["parameters"]] == ["course_id"]
