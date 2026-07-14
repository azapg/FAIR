from datetime import datetime
from uuid import uuid4

from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Submission,
    SubmissionResult,
    SubmissionStatus,
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
)
from fair_platform.backend.data.models.submitter import Submitter
from tests.conftest import get_auth_token


def _create_result(test_db, *, instructor_id, student_id):
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
        workflow = Workflow(
            id=uuid4(),
            course=course,
            name="Legacy grading workflow",
            description=None,
            created_by=instructor_id,
            created_at=datetime.utcnow(),
            steps=[],
        )
        submitter = Submitter(
            id=uuid4(),
            name="Student",
            email="student@test.com",
            user_id=student_id,
            is_synthetic=False,
        )
        session.add_all([course, assignment, workflow, submitter])
        session.flush()

        submission = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=instructor_id,
            submitted_at=datetime.utcnow(),
            status=SubmissionStatus.graded,
        )
        session.add(submission)
        session.flush()

        run = WorkflowRun(
            id=uuid4(),
            workflow_id=workflow.id,
            run_by=instructor_id,
            started_at=datetime.utcnow(),
            finished_at=datetime.utcnow(),
            status=WorkflowRunStatus.success,
            logs={"history": []},
            submissions=[submission],
        )
        session.add(run)
        session.flush()

        submission.official_run_id = run.id
        result = SubmissionResult(
            id=uuid4(),
            submission_id=submission.id,
            workflow_run_id=run.id,
            score=91,
            feedback="Teacher-only legacy result",
            graded_at=datetime.utcnow(),
        )
        session.add(result)
        session.commit()
        return result.id


def _headers(test_client, email):
    token = get_auth_token(test_client, email)
    return {"Authorization": f"Bearer {token}"}


def test_deprecated_result_reads_are_course_scoped(
    test_client,
    test_db,
    professor_user,
    student_user,
    admin_user,
):
    result_id = _create_result(
        test_db,
        instructor_id=professor_user.id,
        student_id=student_user.id,
    )

    owner_response = test_client.get(
        f"/api/submission-results/{result_id}",
        headers=_headers(test_client, professor_user.email),
    )
    assert owner_response.status_code == 200

    admin_response = test_client.get(
        f"/api/submission-results/{result_id}",
        headers=_headers(test_client, admin_user.email),
    )
    assert admin_response.status_code == 200

    student_response = test_client.get(
        f"/api/submission-results/{result_id}",
        headers=_headers(test_client, student_user.email),
    )
    assert student_response.status_code == 403


def test_deprecated_result_list_does_not_leak_to_non_owner(
    test_client,
    test_db,
    professor_user,
    student_user,
):
    result_id = _create_result(
        test_db,
        instructor_id=professor_user.id,
        student_id=student_user.id,
    )

    owner_response = test_client.get(
        "/api/submission-results/",
        headers=_headers(test_client, professor_user.email),
    )
    assert owner_response.status_code == 200
    assert [row["id"] for row in owner_response.json()] == [str(result_id)]

    student_response = test_client.get(
        "/api/submission-results/",
        headers=_headers(test_client, student_user.email),
    )
    assert student_response.status_code == 200
    assert student_response.json() == []
