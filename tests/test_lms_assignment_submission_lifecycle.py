from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.data.models.submission import Submission
from fair_platform.backend.data.models.user import User, UserRole
from tests.conftest import get_auth_token


def _user(session, name: str, role: UserRole) -> User:
    user = User(
        id=uuid4(),
        name=name,
        email=f"{name.lower()}-{uuid4().hex[:6]}@test.com",
        role=role,
        password_hash=hash_password("test_password_123"),
    )
    session.add(user)
    session.commit()
    return user


def _auth(client, user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {get_auth_token(client, str(user.email))}"}


def _setup(session, *, allow_resubmissions: bool = True):
    owner = _user(session, "Owner", UserRole.instructor)
    student = _user(session, "Student", UserRole.student)
    outsider = _user(session, "Outsider", UserRole.student)
    course = Course(id=uuid4(), name="LMS", instructor_id=owner.id)
    assignment = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Essay",
        deadline=datetime.utcnow() - timedelta(minutes=1),
        max_grade={"type": "points", "value": 100},
        status=AssignmentStatus.draft,
        allow_resubmissions=allow_resubmissions,
    )
    session.add_all([course, assignment])
    session.flush()
    session.add(Enrollment(id=uuid4(), user_id=student.id, course_id=course.id))
    session.commit()
    return owner, student, outsider, course, assignment


def test_draft_is_hidden_until_staff_publishes(test_client, test_db):
    with test_db() as session:
        owner, student, _, course, assignment = _setup(session)

    hidden = test_client.get(
        f"/api/assignments/?course_id={course.id}", headers=_auth(test_client, student)
    )
    assert hidden.status_code == 200
    assert hidden.json() == []
    assert test_client.get(
        f"/api/assignments/{assignment.id}", headers=_auth(test_client, student)
    ).status_code == 404

    published = test_client.patch(
        f"/api/assignments/{assignment.id}/status",
        json={"status": "published"},
        headers=_auth(test_client, owner),
    )
    assert published.status_code == 200
    assert published.json()["publishedAt"] is not None
    visible = test_client.get(
        f"/api/assignments/?course_id={course.id}", headers=_auth(test_client, student)
    )
    assert [item["id"] for item in visible.json()] == [str(assignment.id)]


def test_student_submission_is_owned_late_and_attempted(test_client, test_db):
    with test_db() as session:
        owner, student, outsider, _, assignment = _setup(session)
        assignment.status = AssignmentStatus.published
        session.commit()

    first = test_client.post(
        "/api/submissions/",
        data={"assignment_id": str(assignment.id)},
        headers=_auth(test_client, student),
    )
    assert first.status_code == 201
    assert first.json()["submitter"]["userId"] == str(student.id)
    assert first.json()["submitter"]["isSynthetic"] is False
    assert first.json()["attemptNumber"] == 1
    assert first.json()["isLate"] is True

    second = test_client.post(
        "/api/submissions/",
        data={"assignment_id": str(assignment.id)},
        headers=_auth(test_client, student),
    )
    assert second.status_code == 201
    assert second.json()["attemptNumber"] == 2

    with test_db() as session:
        first_submission = session.get(Submission, UUID(first.json()["id"]))
        first_submission.draft_score = 77
        first_submission.draft_feedback = "Private draft"
        session.commit()

    own = test_client.get(
        f"/api/submissions/{first.json()['id']}", headers=_auth(test_client, student)
    )
    assert own.status_code == 200
    assert own.json()["draftScore"] is None
    assert own.json()["draftFeedback"] is None
    assert test_client.get(
        f"/api/submissions/{first.json()['id']}", headers=_auth(test_client, outsider)
    ).status_code == 403


def test_resubmission_policy_and_explicit_synthetic_path(test_client, test_db):
    with test_db() as session:
        owner, student, _, _, assignment = _setup(session, allow_resubmissions=False)
        assignment.status = AssignmentStatus.published
        session.commit()

    first = test_client.post(
        "/api/submissions/",
        data={"assignment_id": str(assignment.id)},
        headers=_auth(test_client, student),
    )
    assert first.status_code == 201
    duplicate = test_client.post(
        "/api/submissions/",
        data={"assignment_id": str(assignment.id)},
        headers=_auth(test_client, student),
    )
    assert duplicate.status_code == 409

    synthetic = test_client.post(
        "/api/submissions/synthetic",
        data={"assignment_id": str(assignment.id), "submitter_name": "Research Subject"},
        headers=_auth(test_client, owner),
    )
    assert synthetic.status_code == 201
    assert synthetic.json()["submitter"]["isSynthetic"] is True


def test_roster_gradebook_queue_and_returned_grade(test_client, test_db):
    with test_db() as session:
        owner, student, second_student, course, assignment = _setup(session)
        assignment.status = AssignmentStatus.published
        session.add(Enrollment(id=uuid4(), user_id=second_student.id, course_id=course.id))
        session.commit()

    initial_todo = test_client.get(
        "/api/lms/todo", headers=_auth(test_client, student)
    ).json()
    assert initial_todo[0]["assignmentId"] == str(assignment.id)
    assert initial_todo[0]["state"] == "missing"

    submitted = test_client.post(
        "/api/submissions/",
        data={"assignment_id": str(assignment.id)},
        headers=_auth(test_client, student),
    )
    assert submitted.status_code == 201
    submission_id = submitted.json()["id"]
    assert test_client.get(
        "/api/lms/todo", headers=_auth(test_client, student)
    ).json()[0]["state"] == "submitted"

    student_comment = test_client.post(
        f"/api/lms/submissions/{submission_id}/comments",
        json={"body": "Could you check my second paragraph?"},
        headers=_auth(test_client, student),
    )
    assert student_comment.status_code == 201
    assert test_client.get(
        f"/api/lms/submissions/{submission_id}/comments",
        headers=_auth(test_client, owner),
    ).json()[0]["authorName"] == "Student"
    assert test_client.get(
        f"/api/lms/submissions/{submission_id}/comments",
        headers=_auth(test_client, second_student),
    ).status_code == 403
    staff_reply = test_client.post(
        f"/api/lms/submissions/{submission_id}/comments",
        json={"body": "Yes, I will review it privately."},
        headers=_auth(test_client, owner),
    )
    assert staff_reply.status_code == 201

    gradebook = test_client.get(
        f"/api/lms/courses/{course.id}/gradebook", headers=_auth(test_client, owner)
    )
    assert gradebook.status_code == 200
    rows = {row["userId"]: row for row in gradebook.json()["rows"]}
    assert rows[str(student.id)]["cells"][0]["state"] == "submitted"
    assert rows[str(second_student.id)]["cells"][0]["state"] == "missing"

    queue = test_client.get(
        f"/api/lms/courses/{course.id}/grading-queue", headers=_auth(test_client, owner)
    )
    assert queue.status_code == 200
    assert [item["submissionId"] for item in queue.json()] == [submission_id]

    draft = test_client.patch(
        f"/api/submissions/{submission_id}/draft",
        json={"score": 91, "feedback": "Clear argument"},
        headers=_auth(test_client, owner),
    )
    assert draft.status_code == 200
    returned = test_client.post(
        f"/api/submissions/{submission_id}/return", headers=_auth(test_client, owner)
    )
    assert returned.status_code == 200

    refreshed = test_client.get(
        f"/api/lms/courses/{course.id}/gradebook", headers=_auth(test_client, owner)
    ).json()
    refreshed_rows = {row["userId"]: row for row in refreshed["rows"]}
    assert refreshed_rows[str(student.id)]["cells"][0]["state"] == "returned"
    assert refreshed_rows[str(student.id)]["cells"][0]["score"] == 91
    assert test_client.get(
        f"/api/lms/courses/{course.id}/grading-queue", headers=_auth(test_client, owner)
    ).json() == []
    assert test_client.get(
        "/api/lms/todo", headers=_auth(test_client, student)
    ).json() == []

    student_view = test_client.get(
        f"/api/submissions/{submission_id}", headers=_auth(test_client, student)
    ).json()
    assert student_view["publishedScore"] == 91
    assert student_view["publishedFeedback"] == "Clear argument"
    assert student_view["draftScore"] is None
    notifications = test_client.get(
        "/api/lms/notifications", headers=_auth(test_client, student)
    ).json()
    assert notifications[0]["kind"] == "grade_returned"
