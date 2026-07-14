from datetime import datetime, timezone
from uuid import uuid4

from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Submission,
    SubmissionStatus,
)
from fair_platform.backend.data.models.submitter import Submitter
from tests.conftest import get_auth_token


def _create_draft_grade(test_db, *, instructor_id, student_id):
    with test_db() as session:
        course = Course(
            id=uuid4(),
            name="Private grading course",
            description=None,
            instructor_id=instructor_id,
        )
        assignment = Assignment(
            id=uuid4(),
            course=course,
            title="Private assignment",
            description=None,
            deadline=None,
            max_grade={"type": "points", "value": 100},
        )
        submitter = Submitter(
            id=uuid4(),
            name="Student",
            email="student@test.com",
            user_id=student_id,
            is_synthetic=False,
        )
        submission = Submission(
            id=uuid4(),
            assignment=assignment,
            submitter=submitter,
            created_by_id=instructor_id,
            submitted_at=datetime.now(timezone.utc),
            status=SubmissionStatus.graded,
            draft_score=91,
            draft_feedback="Teacher-only draft feedback",
        )
        session.add_all([course, assignment, submitter, submission])
        session.commit()
        return submission.id, assignment.id


def _headers(test_client, email):
    token = get_auth_token(test_client, email)
    return {"Authorization": f"Bearer {token}"}


def test_submission_detail_hides_draft_grade_from_student(
    test_client,
    test_db,
    professor_user,
    student_user,
    admin_user,
):
    submission_id, _ = _create_draft_grade(
        test_db,
        instructor_id=professor_user.id,
        student_id=student_user.id,
    )

    for staff in (professor_user, admin_user):
        response = test_client.get(
            f"/api/submissions/{submission_id}",
            headers=_headers(test_client, staff.email),
        )
        assert response.status_code == 200
        assert response.json()["draftScore"] == 91
        assert response.json()["draftFeedback"] == "Teacher-only draft feedback"

    student_response = test_client.get(
        f"/api/submissions/{submission_id}",
        headers=_headers(test_client, student_user.email),
    )
    assert student_response.status_code == 200
    assert student_response.json()["draftScore"] is None
    assert student_response.json()["draftFeedback"] is None


def test_submission_list_hides_draft_grade_from_student(
    test_client,
    test_db,
    professor_user,
    student_user,
):
    submission_id, assignment_id = _create_draft_grade(
        test_db,
        instructor_id=professor_user.id,
        student_id=student_user.id,
    )

    owner_response = test_client.get(
        f"/api/submissions/?assignment_id={assignment_id}",
        headers=_headers(test_client, professor_user.email),
    )
    assert owner_response.status_code == 200
    assert owner_response.json()[0]["id"] == str(submission_id)
    assert owner_response.json()[0]["draftScore"] == 91

    student_response = test_client.get(
        f"/api/submissions/?assignment_id={assignment_id}",
        headers=_headers(test_client, student_user.email),
    )
    assert student_response.status_code == 200
    assert student_response.json()[0]["id"] == str(submission_id)
    assert student_response.json()[0]["draftScore"] is None
    assert student_response.json()[0]["draftFeedback"] is None
