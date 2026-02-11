from uuid import uuid4
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.submission_event import SubmissionEvent, SubmissionEventType
from fair_platform.backend.data.models.workflow import Workflow
from fair_platform.backend.data.models.workflow_run import WorkflowRun, WorkflowRunStatus
from tests.conftest import get_auth_token


def test_get_submission_timeline_populates_fields(test_client: TestClient, test_db, professor_user, admin_user):
    """Test that /submissions/{id}/timeline populates actor and workflow_run fields."""
    with test_db() as session:
        # 1. Setup basic data
        course = Course(
            id=uuid4(),
            name="Timeline Course",
            instructor_id=professor_user.id,
        )
        session.add(course)
        
        assignment = Assignment(
            id=uuid4(),
            course_id=course.id,
            title="Timeline Assignment",
            max_grade={"points": 100},
        )
        session.add(assignment)
        
        submitter = Submitter(
            id=uuid4(),
            name="Student T",
            user_id=None,
        )
        session.add(submitter)
        
        submission = Submission(
            id=uuid4(),
            assignment_id=assignment.id,
            submitter_id=submitter.id,
            created_by_id=professor_user.id,
            status=SubmissionStatus.submitted,
        )
        session.add(submission)
        
        workflow = Workflow(
            id=uuid4(),
            course_id=course.id,
            name="Timeline Workflow",
            created_by=professor_user.id,
            created_at=datetime.utcnow(),
        )
        session.add(workflow)
        
        workflow_run = WorkflowRun(
            id=uuid4(),
            workflow_id=workflow.id,
            run_by=admin_user.id,
            status=WorkflowRunStatus.success,
        )
        session.add(workflow_run)
        session.commit()
        
        # 2. Add events
        # Event 1: Manual edit by professor
        event_manual = SubmissionEvent(
            id=uuid4(),
            submission_id=submission.id,
            event_type=SubmissionEventType.manual_edit,
            actor_id=professor_user.id,
            details={"score": {"old": None, "new": 85}},
        )
        
        # Event 2: AI graded by workflow run
        event_ai = SubmissionEvent(
            id=uuid4(),
            submission_id=submission.id,
            event_type=SubmissionEventType.ai_graded,
            workflow_run_id=workflow_run.id,
            details={"score": 85},
        )
        
        session.add_all([event_manual, event_ai])
        session.commit()
        
        submission_id = submission.id

    # 3. Call the API
    token = get_auth_token(test_client, professor_user.email)
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.get(f"/api/submissions/{submission_id}/timeline", headers=headers)
    
    assert response.status_code == 200
    timeline = response.json()
    assert len(timeline) == 2
    
    # Check manual edit event
    manual_event = next(e for e in timeline if e["eventType"] == "manual_edit")
    assert manual_event.get("actorId") is None
    assert manual_event["actor"] is not None
    assert manual_event["actor"]["name"] == professor_user.name
    assert manual_event["workflowRun"] is None
    
    # Check AI graded event
    ai_event = next(e for e in timeline if e["eventType"] == "ai_graded")
    assert ai_event.get("workflowRunId") is None
    assert ai_event["workflowRun"] is not None
    assert ai_event["workflowRun"]["id"] == str(workflow_run.id)
    assert ai_event["workflowRun"]["runner"]["name"] == admin_user.name
    assert ai_event["actor"] is None
