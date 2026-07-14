from uuid import uuid4

from fastapi.testclient import TestClient

from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.submission_event import SubmissionEvent, SubmissionEventType
from fair_platform.backend.data.models.execution import Execution, ExecutionKind, ExecutionStatus
from tests.conftest import get_auth_token


def test_get_submission_timeline_populates_fields(test_client: TestClient, test_db, professor_user, admin_user):
    """The submission timeline exposes canonical Execution context."""
    with test_db() as session:
        # 1. Setup basic data
        professor_user.is_verified = True
        session.add(professor_user)
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
        
        execution_id = uuid4()
        execution = Execution(
            id=execution_id,
            root_execution_id=execution_id,
            course_id=course.id,
            assignment_id=assignment.id,
            initiated_by_user_id=admin_user.id,
            kind=ExecutionKind.flow,
            status=ExecutionStatus.completed,
            input={},
        )
        session.add(execution)
        session.commit()
        
        # 2. Add events
        # Event 1: Manual edit by professor
        event_manual = SubmissionEvent(
            id=uuid4(),
            submission_id=submission.id,
            event_type=SubmissionEventType.draft_manually_edited,
            actor_id=professor_user.id,
            details={"score": {"old": None, "new": 85}},
        )
        
        # Event 2: automated result recorded by an Execution
        event_ai = SubmissionEvent(
            id=uuid4(),
            submission_id=submission.id,
            event_type=SubmissionEventType.ai_initial_result_recorded,
            execution_id=execution.id,
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
    manual_event = next(
        e for e in timeline if e["eventType"] == "draft_manually_edited"
    )
    assert manual_event.get("actorId") is None
    assert manual_event["actor"] is not None
    assert manual_event["actor"]["name"] == professor_user.name
    assert "id" not in manual_event["actor"]
    assert "email" not in manual_event["actor"]
    assert "role" not in manual_event["actor"]
    assert manual_event["execution"] is None
    
    # Check AI graded event
    ai_event = next(
        e for e in timeline if e["eventType"] == "ai_initial_result_recorded"
    )
    assert ai_event.get("executionId") is None
    assert ai_event["execution"] is not None
    assert ai_event["execution"]["id"] == str(execution.id)
    assert ai_event["execution"]["status"] == "completed"
    assert ai_event["execution"]["kind"] == "flow"
    assert "input" not in ai_event["execution"]
    assert "outputSummary" not in ai_event["execution"]
    assert ai_event["actor"] is None
