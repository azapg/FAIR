from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

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
from fair_platform.backend.services.job_queue import LocalJobQueue
from fair_platform.backend.services import workflow_runner as workflow_runner_module
from fair_platform.backend.services.workflow_runner import WorkflowRunEventBroker, WorkflowRunner
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
            status=SubmissionStatus.submitted,
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
    @pytest.mark.asyncio
    async def test_workflow_runner_persists_grader_results_into_submission_state(
        self, test_db, professor_user, monkeypatch
    ):
        monkeypatch.setattr(workflow_runner_module, "get_session", test_db)
        data = _create_workflow_run_fixture(
            test_db,
            instructor_id=professor_user.id,
            runner_id=professor_user.id,
        )
        runner = WorkflowRunner(LocalJobQueue(), WorkflowRunEventBroker())

        await runner._persist_submission_results(
            data["run"].id,
            {
                "plugin_type": "grader",
                "results": [
                    {
                        "submission_id": str(data["submission"].id),
                        "grade": 91,
                        "feedback": "Strong work",
                        "metadata": {"source": "test"},
                    }
                ],
            },
        )

        with test_db() as session:
            submission = session.get(Submission, data["submission"].id)
            assert submission is not None
            assert submission.draft_score == 91
            assert submission.draft_feedback == "Strong work"
            assert submission.status == SubmissionStatus.graded

            result = (
                session.query(SubmissionResult)
                .filter(
                    SubmissionResult.submission_id == data["submission"].id,
                    SubmissionResult.workflow_run_id == data["run"].id,
                )
                .first()
            )
            assert result is not None
            assert result.score == 91
            assert result.feedback == "Strong work"

    def test_create_workflow_run_returns_pending_run_for_step_workflow(
        self, test_client: TestClient, test_db, professor_user
    ):
        with test_db() as session:
            course = Course(
                id=uuid4(),
                name="Pipeline Course",
                description="Course used for pipeline workflow runs",
                instructor_id=professor_user.id,
            )
            workflow = Workflow(
                id=uuid4(),
                course_id=course.id,
                name="Pipeline Workflow",
                description="workflow with steps",
                created_by=professor_user.id,
                created_at=datetime.utcnow(),
                steps=[
                    {
                        "id": "review-step",
                        "order": 0,
                        "pluginType": "reviewer",
                        "plugin": {
                            "pluginId": "local.reviewer",
                            "extensionId": "missing.extension",
                            "name": "Reviewer",
                            "pluginType": "reviewer",
                            "action": "plugin.review",
                            "settingsSchema": {
                                "reviewTone": {
                                    "fieldType": "text",
                                    "label": "Review Tone",
                                    "description": "Tone for generated comments.",
                                    "required": False,
                                    "default": "concise",
                                    "minLength": 1,
                                    "maxLength": 100,
                                }
                            },
                            "settings": {},
                            "id": "local.reviewer",
                            "type": "reviewer",
                            "source": "missing.extension",
                        },
                        "settings": {},
                    }
                ],
            )
            assignment = Assignment(
                id=uuid4(),
                course_id=course.id,
                title="Pipeline Assignment",
                description="assignment under test",
                deadline=None,
                max_grade={"type": "points", "value": 100},
            )
            submitter = Submitter(
                id=uuid4(),
                name="Pipeline Student",
                email="pipeline@example.com",
                user_id=None,
            )
            submission = Submission(
                id=uuid4(),
                assignment_id=assignment.id,
                submitter_id=submitter.id,
                created_by_id=professor_user.id,
                submitted_at=datetime.utcnow(),
                status=SubmissionStatus.submitted,
            )
            session.add_all([course, workflow, assignment, submitter, submission])
            session.commit()

        token = get_auth_token(test_client, professor_user.email)
        response = test_client.post(
            "/api/workflow-runs",
            json={"workflowId": str(workflow.id), "submissionIds": [str(submission.id)]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 202
        body = response.json()
        assert body["workflowId"] == str(workflow.id)
        assert body["status"] == "pending"
        assert body["stepStates"] == []

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
        assert run["runner"]['id'] == str(admin_user.id)
        assert run["submissions"]
        assert run["submissions"][0]["assignmentId"] == str(data["assignment"].id)

    @pytest.mark.parametrize("mode", ["COMMUNITY", "ENTERPRISE"])
    def test_student_cannot_access_workflow_runs(
        self,
        test_client: TestClient,
        test_db,
        professor_user,
        student_user,
        monkeypatch,
        mode,
    ):
        monkeypatch.setenv("FAIR_DEPLOYMENT_MODE", mode)
        data = _create_workflow_run_fixture(
            test_db, instructor_id=professor_user.id, runner_id=professor_user.id
        )

        token = get_auth_token(test_client, student_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get(
            f"/api/workflow-runs?course_id={data['course'].id}", headers=headers
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        ("mode", "expected_status"),
        [("COMMUNITY", 200), ("ENTERPRISE", 403)],
    )
    def test_user_course_owner_mode_controls_workflow_run_access(
        self,
        test_client: TestClient,
        test_db,
        student_user,
        monkeypatch,
        mode,
        expected_status,
    ):
        monkeypatch.setenv("FAIR_DEPLOYMENT_MODE", mode)
        data = _create_workflow_run_fixture(
            test_db, instructor_id=student_user.id, runner_id=student_user.id
        )

        token = get_auth_token(test_client, student_user.email)
        headers = {"Authorization": f"Bearer {token}"}

        response = test_client.get(
            f"/api/workflow-runs?course_id={data['course'].id}", headers=headers
        )
        assert response.status_code == expected_status

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
                status=SubmissionStatus.submitted,
            )
            submission_b = Submission(
                id=uuid4(),
                assignment_id=assignment_b.id,
                submitter_id=submitter.id,
                created_by_id=professor_user.id,
                submitted_at=datetime.utcnow(),
                status=SubmissionStatus.submitted,
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
