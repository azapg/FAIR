from datetime import datetime
from uuid import uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Submission,
    SubmissionStatus,
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
)
from fair_platform.backend.data.models.submitter import Submitter
from tests.conftest import get_auth_token


def _create_workflow_run_fixture(test_db, *, instructor_id, runner_id):
    with test_db() as session:
        course = Course(
            id=uuid4(),
            name="Testing Course",
            description="Course used for workflow runs",
            instructor_id=instructor_id,
        )

        workflow = Workflow(
            id=uuid4(),
            course_id=course.id,
            name="Test Workflow",
            description="workflow for tests",
            created_by=instructor_id,
            created_at=datetime.utcnow(),
        )

        assignment = Assignment(
            id=uuid4(),
            course_id=course.id,
            title="Test Assignment",
            description="assignment under test",
            deadline=None,
            max_grade={"type": "points", "value": 100},
        )

        submitter = Submitter(
            id=uuid4(),
            name="Student A",
            email="student@example.com",
            user_id=None,
        )

        submission = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=instructor_id,
            submitted_at=datetime.utcnow(),
            status=SubmissionStatus.pending,
        )

        run = WorkflowRun(
            id=uuid4(),
            workflow_id=workflow.id,
            run_by=runner_id,
            started_at=datetime.utcnow(),
            finished_at=None,
            status=WorkflowRunStatus.running,
            logs={"history": []},
            submissions=[submission],
        )

        session.add_all([course, workflow, assignment, submitter, submission, run])
        session.commit()
        session.refresh(run)
        session.refresh(assignment)
        session.refresh(workflow)
        session.refresh(course)

        return {
            "course": course,
            "workflow": workflow,
            "assignment": assignment,
            "submission": submission,
            "run": run,
        }


class TestWorkflowRunsAPI:
    def test_professor_can_list_course_runs(self, test_client: TestClient, test_db, professor_user, admin_user):
        data = _create_workflow_run_fixture(
            test_db, instructor_id=professor_user.id, runner_id=admin_user.id
        )

        token = get_auth_token(test_client, professor_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get(
            f"/api/workflow-runs?course_id={data['course'].id}", headers=headers
        )

        assert response.status_code == 200
        runs = response.json()
        assert len(runs) == 1
        run = runs[0]
        assert run["workflowId"] == str(data["workflow"].id)
        assert run["runBy"] == str(admin_user.id)
        assert run["submissions"]
        assert run["submissions"][0]["assignmentId"] == str(data["assignment"].id)

    def test_student_cannot_access_workflow_runs(self, test_client: TestClient, test_db, professor_user, student_user):
        data = _create_workflow_run_fixture(
            test_db, instructor_id=professor_user.id, runner_id=professor_user.id
        )

        token = get_auth_token(test_client, student_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get(
            f"/api/workflow-runs?course_id={data['course'].id}", headers=headers
        )
        assert response.status_code == 403

    def test_admin_can_filter_runs_by_assignment(
        self, test_client: TestClient, test_db, professor_user, admin_user
    ):
        with test_db() as session:
            course = Course(
                id=uuid4(),
                name="Filtering Course",
                description="Course for filtering tests",
                instructor_id=professor_user.id,
            )
            workflow = Workflow(
                id=uuid4(),
                course_id=course.id,
                name="Filter Workflow",
                description="workflow for filtering",
                created_by=professor_user.id,
                created_at=datetime.utcnow(),
            )
            assignment_a = Assignment(
                id=uuid4(),
                course_id=course.id,
                title="Assignment A",
                description="first assignment",
                deadline=None,
                max_grade={"type": "points", "value": 50},
            )
            assignment_b = Assignment(
                id=uuid4(),
                course_id=course.id,
                title="Assignment B",
                description="second assignment",
                deadline=None,
                max_grade={"type": "points", "value": 50},
            )
            submitter = Submitter(
                id=uuid4(), name="Student B", email="studentb@example.com", user_id=None
            )
            submission_a = Submission(
                id=uuid4(),
                assignment_id=assignment_a.id,
                submitter_id=submitter.id,
                created_by_id=professor_user.id,
                submitted_at=datetime.utcnow(),
                status=SubmissionStatus.pending,
            )
            submission_b = Submission(
                id=uuid4(),
                assignment_id=assignment_b.id,
                submitter_id=submitter.id,
                created_by_id=professor_user.id,
                submitted_at=datetime.utcnow(),
                status=SubmissionStatus.pending,
            )
            run_a = WorkflowRun(
                id=uuid4(),
                workflow_id=workflow.id,
                run_by=admin_user.id,
                status=WorkflowRunStatus.success,
                started_at=datetime.utcnow(),
                finished_at=datetime.utcnow(),
                submissions=[submission_a],
            )
            run_b = WorkflowRun(
                id=uuid4(),
                workflow_id=workflow.id,
                run_by=admin_user.id,
                status=WorkflowRunStatus.pending,
                started_at=datetime.utcnow(),
                finished_at=None,
                submissions=[submission_b],
            )

            session.add_all(
                [
                    course,
                    workflow,
                    assignment_a,
                    assignment_b,
                    submitter,
                    submission_a,
                    submission_b,
                    run_a,
                    run_b,
                ]
            )
            session.commit()

        token = get_auth_token(test_client, admin_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get(
            f"/api/workflow-runs?assignment_id={assignment_a.id}", headers=headers
        )
        assert response.status_code == 200
        runs = response.json()
        assert len(runs) == 1
        assert runs[0]["id"] == str(run_a.id)
        assert runs[0]["submissions"][0]["assignmentId"] == str(assignment_a.id)
