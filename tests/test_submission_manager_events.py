from datetime import datetime
from uuid import uuid4

from fair_platform.backend.api.routers.auth import hash_password
from fair_platform.backend.data.models.assignment import Assignment
from fair_platform.backend.data.models.course import Course
from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submission_event import SubmissionEvent, SubmissionEventType
from fair_platform.backend.data.models.submitter import Submitter
from fair_platform.backend.data.models.user import User, UserRole
from fair_platform.backend.data.models.workflow import Workflow
from fair_platform.backend.data.models.workflow_run import WorkflowRun, WorkflowRunStatus
from fair_platform.backend.services.submission_manager import SubmissionManager


def _build_submission_graph(session):
    professor = User(
        id=uuid4(),
        name="Professor",
        email=f"prof-{uuid4()}@test.com",
        role=UserRole.professor,
        password_hash=hash_password("test_password_123"),
    )
    session.add(professor)

    course = Course(
        id=uuid4(),
        name="Course",
        description="Course",
        instructor_id=professor.id,
    )
    session.add(course)

    assignment = Assignment(
        id=uuid4(),
        course_id=course.id,
        title="Assignment",
        description="Desc",
        max_grade={"points": 100},
    )
    session.add(assignment)

    submitter = Submitter(
        id=uuid4(),
        name="Student",
        email=None,
        user_id=None,
        is_synthetic=True,
        created_at=datetime.utcnow(),
    )
    session.add(submitter)

    submission = Submission(
        id=uuid4(),
        assignment_id=assignment.id,
        submitter_id=submitter.id,
        created_by_id=professor.id,
        submitted_at=datetime.utcnow(),
        status=SubmissionStatus.submitted,
    )
    session.add(submission)

    workflow = Workflow(
        id=uuid4(),
        course_id=course.id,
        name="Workflow",
        description="Wf",
        created_by=professor.id,
        created_at=datetime.utcnow(),
    )
    session.add(workflow)

    workflow_run = WorkflowRun(
        id=uuid4(),
        workflow_id=workflow.id,
        run_by=professor.id,
        status=WorkflowRunStatus.success,
    )
    session.add(workflow_run)
    session.commit()

    return professor, submission, workflow_run


def test_record_ai_result_splits_initial_vs_regrade(test_db):
    with test_db() as session:
        _, submission, workflow_run = _build_submission_graph(session)
        manager = SubmissionManager(session)

        manager.record_ai_result(
            submission_id=submission.id,
            score=82.0,
            feedback="Initial feedback",
            workflow_run_id=workflow_run.id,
        )
        manager.record_ai_result(
            submission_id=submission.id,
            score=91.0,
            feedback="Updated feedback",
            workflow_run_id=workflow_run.id,
        )
        session.commit()

        events = (
            session.query(SubmissionEvent)
            .filter(SubmissionEvent.submission_id == submission.id)
            .order_by(SubmissionEvent.created_at)
            .all()
        )
        assert len(events) == 2
        assert events[0].event_type == SubmissionEventType.ai_initial_result_recorded.value
        assert events[0].details["attempt_index"] == 1
        assert events[1].event_type == SubmissionEventType.ai_regrade_result_recorded.value
        assert events[1].details["attempt_index"] == 2


def test_return_to_student_emits_return_and_status_transition(test_db):
    with test_db() as session:
        professor, submission, _ = _build_submission_graph(session)
        submission.status = SubmissionStatus.graded
        submission.draft_score = 88.0
        submission.draft_feedback = "Ready to publish"
        session.commit()

        manager = SubmissionManager(session)
        manager.return_to_student(submission.id, professor)
        session.commit()

        events = (
            session.query(SubmissionEvent)
            .filter(SubmissionEvent.submission_id == submission.id)
            .order_by(SubmissionEvent.created_at)
            .all()
        )
        assert len(events) == 2
        assert events[0].event_type == SubmissionEventType.returned_to_student.value
        assert events[1].event_type == SubmissionEventType.status_transitioned.value
        assert events[1].details["from_status"] == SubmissionStatus.graded.value
        assert events[1].details["to_status"] == SubmissionStatus.returned.value
        assert events[1].details["reason"] == "returned_to_student"
