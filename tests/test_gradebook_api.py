from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.assignment import Assignment, AssignmentStatus
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.enrollment import Enrollment
from fair_platform.backend.data.models.lms_gradebook import GradeEntry
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.services.gradebook import ensure_assignment_grade_item
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
    outsider = _user(session, "Outsider", UserRole.student)
    course = Course(id=uuid4(), name="Gradebook", instructor_id=owner.id)
    session.add(course)
    session.flush()
    session.add_all(
        [
            Enrollment(id=uuid4(), course_id=course.id, user_id=owner.id, role="owner"),
            Enrollment(
                id=uuid4(), course_id=course.id, user_id=assistant.id, role="assistant"
            ),
            Enrollment(
                id=uuid4(), course_id=course.id, user_id=student.id, role="student"
            ),
        ]
    )
    assignment = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Essay",
        max_grade={"type": "points", "value": 100},
        status=AssignmentStatus.published,
    )
    submitter = Submitter(
        id=uuid4(),
        name=student.name,
        email=str(student.email),
        user_id=student.id,
        is_synthetic=False,
    )
    session.add_all([assignment, submitter])
    session.flush()
    ensure_assignment_grade_item(session, assignment)
    session.commit()
    return owner, assistant, student, outsider, course, assignment, submitter


def test_gradebook_is_staff_only_and_legacy_response_is_additive(test_client, test_db):
    with test_db() as session:
        owner, assistant, student, outsider, course, assignment, _ = _setup(session)

    forbidden = test_client.get(
        f"/api/lms/courses/{course.id}/gradebook",
        headers=_auth(test_client, student),
    )
    assert forbidden.status_code == 403
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/gradebook",
            headers=_auth(test_client, outsider),
        ).status_code
        == 403
    )

    response = test_client.get(
        f"/api/lms/courses/{course.id}/gradebook",
        headers=_auth(test_client, assistant),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assignments"][0]["id"] == str(assignment.id)
    assert body["rows"][0]["cells"][0]["state"] == "missing"
    assert "categories" in body and "items" in body
    assert "courseTotal" in body["rows"][0]


def test_manual_controls_validate_course_scope_membership_and_archive(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, outsider, course, assignment, _ = _setup(session)
        other_course = Course(id=uuid4(), name="Other", instructor_id=owner.id)
        session.add(other_course)
        session.commit()

    category = test_client.post(
        f"/api/lms/courses/{course.id}/gradebook/categories",
        json={"name": "Projects", "weight": 100},
        headers=_auth(test_client, owner),
    )
    assert category.status_code == 201
    other_category = test_client.post(
        f"/api/lms/courses/{other_course.id}/gradebook/categories",
        json={"name": "Other"},
        headers=_auth(test_client, owner),
    ).json()
    wrong_scope = test_client.post(
        f"/api/lms/courses/{course.id}/gradebook/items",
        json={
            "title": "Presentation",
            "maxPoints": 20,
            "categoryId": other_category["id"],
        },
        headers=_auth(test_client, owner),
    )
    assert wrong_scope.status_code == 404

    item = test_client.post(
        f"/api/lms/courses/{course.id}/gradebook/items",
        json={
            "title": "Presentation",
            "maxPoints": 20,
            "categoryId": category.json()["id"],
        },
        headers=_auth(test_client, owner),
    )
    assert item.status_code == 201
    outsider_entry = test_client.put(
        f"/api/lms/courses/{course.id}/gradebook/items/{item.json()['id']}/entries/{outsider.id}",
        json={"status": "graded", "pointsEarned": 10},
        headers=_auth(test_client, owner),
    )
    assert outsider_entry.status_code == 400
    extra_credit = test_client.put(
        f"/api/lms/courses/{course.id}/gradebook/items/{item.json()['id']}/entries/{student.id}",
        json={"status": "graded", "pointsEarned": 20.01},
        headers=_auth(test_client, owner),
    )
    assert extra_credit.status_code == 400
    assert "maximum points" in extra_credit.json()["detail"]
    valid_entry = test_client.put(
        f"/api/lms/courses/{course.id}/gradebook/items/{item.json()['id']}/entries/{student.id}",
        json={"status": "graded", "pointsEarned": 18},
        headers=_auth(test_client, owner),
    )
    assert valid_entry.status_code == 200
    lowered_maximum = test_client.patch(
        f"/api/lms/courses/{course.id}/gradebook/items/{item.json()['id']}",
        json={"maxPoints": 17},
        headers=_auth(test_client, owner),
    )
    assert lowered_maximum.status_code == 400
    assert "existing released entry" in lowered_maximum.json()["detail"]
    cleared_entry = test_client.put(
        f"/api/lms/courses/{course.id}/gradebook/items/{item.json()['id']}/entries/{student.id}",
        json={"status": "missing"},
        headers=_auth(test_client, owner),
    )
    assert cleared_entry.status_code == 200
    assert cleared_entry.json()["status"] == "missing"
    assert cleared_entry.json()["pointsEarned"] is None

    with test_db() as session:
        enrollment = (
            session.query(Enrollment)
            .filter(
                Enrollment.course_id == course.id,
                Enrollment.user_id == student.id,
            )
            .one()
        )
        enrollment.status = "removed"
        session.commit()
    removed_entry = test_client.put(
        f"/api/lms/courses/{course.id}/gradebook/items/{item.json()['id']}/entries/{student.id}",
        json={"status": "graded", "pointsEarned": 17},
        headers=_auth(test_client, owner),
    )
    assert removed_entry.status_code == 400

    with test_db() as session:
        session.get(Course, course.id).is_archived = True
        session.commit()
    archived_write = test_client.post(
        f"/api/lms/courses/{course.id}/gradebook/items",
        json={"title": "Blocked", "maxPoints": 10},
        headers=_auth(test_client, owner),
    )
    assert archived_write.status_code == 400
    archived_submission = test_client.post(
        "/api/submissions/synthetic",
        data={
            "assignment_id": str(assignment.id),
            "submitter_name": "Archived learner",
        },
        headers=_auth(test_client, owner),
    )
    assert archived_submission.status_code == 400
    archived_status_change = test_client.patch(
        f"/api/assignments/{assignment.id}/status",
        json={"status": "closed"},
        headers=_auth(test_client, owner),
    )
    assert archived_status_change.status_code == 400
    with test_db() as session:
        assert (
            session.get(Assignment, assignment.id).status == AssignmentStatus.published
        )
    assert (
        test_client.get(
            f"/api/lms/courses/{course.id}/gradebook",
            headers=_auth(test_client, owner),
        ).status_code
        == 200
    )


def test_return_projects_published_score_and_never_draft(test_client, test_db):
    with test_db() as session:
        owner, _, student, _, course, assignment, submitter = _setup(session)
        submission = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=student.id,
            submitted_at=datetime.utcnow(),
            status=SubmissionStatus.graded,
            draft_score=82,
            draft_feedback="Ready",
        )
        session.add(submission)
        session.commit()
        submission_id = submission.id

    before = test_client.get(
        f"/api/lms/courses/{course.id}/gradebook",
        headers=_auth(test_client, owner),
    ).json()
    assignment_item = next(
        item for item in before["items"] if item["sourceType"] == "assignment"
    )
    assert before["rows"][0]["itemCells"][0]["status"] == "absent"
    with test_db() as session:
        assert session.query(GradeEntry).count() == 0

    invalid_draft = test_client.patch(
        f"/api/submissions/{submission_id}/draft",
        json={"score": -1},
        headers=_auth(test_client, owner),
    )
    assert invalid_draft.status_code == 422

    returned = test_client.post(
        f"/api/submissions/{submission_id}/return",
        headers=_auth(test_client, owner),
    )
    assert returned.status_code == 200
    assert returned.json()["publishedScore"] == 82
    with test_db() as session:
        entry = session.query(GradeEntry).one()
        assert str(entry.grade_item_id) == assignment_item["id"]
        assert float(entry.points_earned) == 82
        assert (
            float(entry.points_earned)
            == session.get(Submission, submission_id).published_score
        )

    revised = test_client.patch(
        f"/api/submissions/{submission_id}/draft",
        json={"score": 91},
        headers=_auth(test_client, owner),
    )
    assert revised.status_code == 200
    with test_db() as session:
        assert float(session.query(GradeEntry).one().points_earned) == 82

    assert (
        test_client.post(
            f"/api/submissions/{submission_id}/return",
            headers=_auth(test_client, owner),
        ).status_code
        == 200
    )
    with test_db() as session:
        entry = session.query(GradeEntry).one()
        submission = session.get(Submission, submission_id)
        assert float(entry.points_earned) == submission.published_score == 91


def test_latest_attempt_and_submission_deletion_keep_grade_entry_in_parity(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, _, course, assignment, submitter = _setup(session)
        older = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=student.id,
            submitted_at=datetime.utcnow(),
            attempt_number=1,
            status=SubmissionStatus.graded,
            draft_score=70,
            draft_feedback="Older",
        )
        newer = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=student.id,
            submitted_at=datetime.utcnow(),
            attempt_number=2,
            status=SubmissionStatus.graded,
            draft_score=88,
            draft_feedback="Newer",
        )
        session.add_all([older, newer])
        session.commit()
        older_id = older.id
        newer_id = newer.id

    assert (
        test_client.post(
            f"/api/submissions/{older_id}/return",
            headers=_auth(test_client, owner),
        ).status_code
        == 200
    )
    with test_db() as session:
        assert session.query(GradeEntry).count() == 0

    assert (
        test_client.post(
            f"/api/submissions/{newer_id}/return",
            headers=_auth(test_client, owner),
        ).status_code
        == 200
    )
    with test_db() as session:
        entry = session.query(GradeEntry).one()
        assert entry.source_id == newer_id
        assert float(entry.points_earned) == 88

    assert (
        test_client.delete(
            f"/api/submissions/{newer_id}",
            headers=_auth(test_client, owner),
        ).status_code
        == 204
    )
    with test_db() as session:
        entry = session.query(GradeEntry).one()
        assert entry.source_id == older_id
        assert float(entry.points_earned) == 70

    with test_db() as session:
        session.get(Course, course.id).is_archived = True
        session.commit()
    blocked = test_client.delete(
        f"/api/submissions/{older_id}",
        headers=_auth(test_client, owner),
    )
    assert blocked.status_code == 400
    with test_db() as session:
        assert session.query(GradeEntry).one().source_id == older_id


def _create_attempt(client, assignment, headers):
    response = client.post(
        "/api/submissions", data={"assignment_id": str(assignment.id)}, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


def _return_attempt(client, submission_id, headers, score=80):
    response = client.patch(
        f"/api/submissions/{submission_id}/draft",
        json={"score": score, "feedback": f"Private feedback {score}"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    response = client.post(f"/api/submissions/{submission_id}/return", headers=headers)
    assert response.status_code == 200, response.text


def _assert_current_grade(client, course, staff, learner, score, submission_id=None):
    book = client.get(f"/api/lms/courses/{course.id}/gradebook", headers=staff).json()
    row = book["rows"][0]
    cell = row["itemCells"][0]
    assert cell["pointsEarned"] == score
    assert cell["sourceId"] == submission_id
    assert cell["releaseState"] == ("absent" if score is None else "released")
    grades = client.get(f"/api/lms/courses/{course.id}/grades", headers=learner).json()
    assert grades["items"][0]["pointsEarned"] == score
    assert grades["items"][0]["submissionId"] == submission_id
    dashboard = client.get("/api/lms/student/dashboard", headers=learner).json()
    progress = dashboard["courseProgress"][0]
    for total in [row["courseTotal"], grades["total"]]:
        assert total["percentage"] == score
        assert total["provisional"] == (score is None)
        assert total["gradedItemCount"] == (0 if score is None else 1)
        assert total["pointsPossible"] == (0 if score is None else 100)
    assert progress["currentGrade"] == score
    assert progress["gradeIsProvisional"] == (score is None)
    return row, grades


def test_resubmission_clears_obsolete_grade_until_latest_attempt_is_returned(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, _, course, assignment, _ = _setup(session)
    staff, learner = _auth(test_client, owner), _auth(test_client, student)
    first = _create_attempt(test_client, assignment, learner)
    _return_attempt(test_client, first["id"], staff)
    _assert_current_grade(test_client, course, staff, learner, 80, first["id"])

    second = _create_attempt(test_client, assignment, learner)
    assert second["attemptNumber"] == 2
    row, _ = _assert_current_grade(test_client, course, staff, learner, None)
    assert row["cells"][0]["state"] == "submitted"
    assert row["cells"][0]["score"] is None
    assert row["cells"][0]["attemptCount"] == 2
    with test_db() as session:
        assert session.query(GradeEntry).count() == 0

    draft = test_client.patch(
        f"/api/submissions/{second['id']}/draft",
        json={"score": 95, "feedback": "Private revision feedback"},
        headers=staff,
    )
    assert draft.status_code == 200
    _, grades = _assert_current_grade(test_client, course, staff, learner, None)
    assert grades["items"][0]["note"] is None
    for path in [
        f"/api/submissions/{second['id']}",
        f"/api/submissions/?assignment_id={assignment.id}",
    ]:
        response = test_client.get(path, headers=learner)
        assert response.status_code == 200
        assert "Private revision feedback" not in response.text
        submissions = (
            response.json() if isinstance(response.json(), list) else [response.json()]
        )
        assert all(
            s["draftScore"] is None and s["draftFeedback"] is None for s in submissions
        )

    # Returning an older attempt must not restore its now-obsolete grade.
    _return_attempt(test_client, first["id"], staff, score=70)
    _assert_current_grade(test_client, course, staff, learner, None)
    returned = test_client.post(
        f"/api/submissions/{second['id']}/return", headers=staff
    )
    assert returned.status_code == 200
    _assert_current_grade(test_client, course, staff, learner, 95, second["id"])
    _return_attempt(test_client, first["id"], staff, score=60)
    _assert_current_grade(test_client, course, staff, learner, 95, second["id"])
    assert (
        test_client.delete(f"/api/submissions/{first['id']}", headers=staff).status_code
        == 204
    )
    _assert_current_grade(test_client, course, staff, learner, 95, second["id"])


def test_rejected_or_failed_resubmission_preserves_released_grade(
    test_client, test_db, monkeypatch
):
    from fair_platform.backend.api.routers import submissions as router

    with test_db() as session:
        owner, _, student, _, course, assignment, _ = _setup(session)
    staff, learner = _auth(test_client, owner), _auth(test_client, student)
    first = _create_attempt(test_client, assignment, learner)
    _return_attempt(test_client, first["id"], staff)
    with test_db() as session:
        session.get(Assignment, assignment.id).allow_resubmissions = False
        session.commit()
    rejected = test_client.post(
        "/api/submissions", data={"assignment_id": str(assignment.id)}, headers=learner
    )
    assert rejected.status_code == 409
    _assert_current_grade(test_client, course, staff, learner, 80, first["id"])
    with test_db() as session:
        session.get(Assignment, assignment.id).allow_resubmissions = True
        session.commit()

    invalid_artifact = test_client.post(
        "/api/submissions",
        data={"assignment_id": str(assignment.id), "artifact_ids": '["invalid"]'},
        headers=learner,
    )
    assert invalid_artifact.status_code == 400
    _assert_current_grade(test_client, course, staff, learner, 80, first["id"])

    original_sync = router.sync_assignment_user_grade_entry

    def fail_after_sync(*args, **kwargs):
        original_sync(*args, **kwargs)
        raise RuntimeError("Simulated failure after grade synchronization")

    monkeypatch.setattr(router, "sync_assignment_user_grade_entry", fail_after_sync)
    failed = test_client.post(
        "/api/submissions", data={"assignment_id": str(assignment.id)}, headers=learner
    )
    assert failed.status_code == 500
    with test_db() as session:
        assert session.query(Submission).count() == 1
        assert session.query(GradeEntry).one().source_id == UUID(first["id"])
    _assert_current_grade(test_client, course, staff, learner, 80, first["id"])


def test_synthetic_submission_does_not_clear_a_real_learners_grade(
    test_client, test_db
):
    with test_db() as session:
        owner, _, student, _, course, assignment, _ = _setup(session)
    staff, learner = _auth(test_client, owner), _auth(test_client, student)
    first = _create_attempt(test_client, assignment, learner)
    _return_attempt(test_client, first["id"], staff)
    synthetic = test_client.post(
        "/api/submissions/synthetic",
        data={"assignment_id": str(assignment.id), "submitter_name": student.name},
        headers=staff,
    )
    assert synthetic.status_code == 201
    _assert_current_grade(test_client, course, staff, learner, 80, first["id"])


def test_concurrent_resubmissions_keep_canonical_latest_grade(test_client, test_db):
    from concurrent.futures import ThreadPoolExecutor

    with test_db() as session:
        owner, _, student, _, course, assignment, _ = _setup(session)
    staff, learner = _auth(test_client, owner), _auth(test_client, student)
    first = _create_attempt(test_client, assignment, learner)
    _return_attempt(test_client, first["id"], staff)
    with ThreadPoolExecutor(max_workers=2) as pool:
        attempts = list(
            pool.map(
                lambda _: _create_attempt(test_client, assignment, learner), range(2)
            )
        )
    _assert_current_grade(test_client, course, staff, learner, None)
    # Concurrent requests can share an attempt number; the existing canonical
    # time/UUID tie-breakers must determine which evidence can be released.
    older, latest = sorted(
        attempts, key=lambda s: (s["attemptNumber"], s["submittedAt"], s["id"])
    )
    _return_attempt(test_client, older["id"], staff, score=70)
    _assert_current_grade(test_client, course, staff, learner, None)
    _return_attempt(test_client, latest["id"], staff, score=95)
    _assert_current_grade(test_client, course, staff, learner, 95, latest["id"])
