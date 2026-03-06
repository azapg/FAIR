import json
from collections.abc import AsyncIterable
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.sse import EventSourceResponse, format_sse_event
from jose import JWTError, jwt
from sqlalchemy.orm import Session, joinedload

from fair_platform.backend.api.routers.auth import ALGORITHM, SECRET_KEY, get_current_user
from fair_platform.backend.api.schema.submission import SubmissionBase
from fair_platform.backend.api.schema.workflow_run import WorkflowRunCreateRequest, WorkflowRunRead, WorkflowRunStepState
from fair_platform.backend.core.security.permissions import (
    has_capability,
    has_capability_and_owner,
)
from fair_platform.backend.data.database import get_session, session_dependency
from fair_platform.backend.data.models import (
    Assignment,
    Course,
    Submission,
    User,
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
)
from fair_platform.backend.services.workflow_runner import WorkflowRunEventBroker, WorkflowRunner
from fair_platform.backend.services.job_queue import LocalJobQueue

router = APIRouter()


def get_workflow_runner(request: Request) -> WorkflowRunner:
    runner = getattr(request.app.state, "workflow_runner", None)
    if runner is None:
        broker = getattr(request.app.state, "workflow_run_event_broker", None)
        if broker is None:
            broker = WorkflowRunEventBroker()
            request.app.state.workflow_run_event_broker = broker
        queue = getattr(request.app.state, "job_queue", None)
        if queue is None:
            queue = LocalJobQueue()
            request.app.state.job_queue = queue
        runner = WorkflowRunner(job_queue=queue, event_broker=broker)
        request.app.state.workflow_runner = runner
    return runner


def get_workflow_event_broker(request: Request) -> WorkflowRunEventBroker:
    broker = getattr(request.app.state, "workflow_run_event_broker", None)
    if broker is None:
        broker = WorkflowRunEventBroker()
        request.app.state.workflow_run_event_broker = broker
    return broker


def _assert_course_access(db: Session, user: User, course_id: UUID):
    course = db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if not has_capability_and_owner(user, "read_workflow_runs", course.instructor_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the course instructor or admin can access these workflow runs",
        )


def _current_user_from_stream_request(request: Request, db: Session) -> User:
    auth_header = request.headers.get("authorization", "").strip()
    token = ""
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
    if not token:
        token = (request.query_params.get("access_token") or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    user = db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def _serialize_run(run: WorkflowRun) -> WorkflowRunRead:
    submissions = [SubmissionBase.model_validate(sub) for sub in run.submissions] if run.submissions else None
    step_states = [WorkflowRunStepState.model_validate(item) for item in (run.step_states or [])]
    return WorkflowRunRead(
        id=run.id,
        workflow_id=run.workflow_id,
        runner=run.runner,
        status=run.status,
        started_at=run.started_at,
        finished_at=run.finished_at,
        logs=run.logs,
        submissions=submissions,
        step_states=step_states,
        request_payload=run.request_payload,
    )


@router.post("/", response_model=WorkflowRunRead, status_code=status.HTTP_202_ACCEPTED)
async def create_workflow_run(
    payload: WorkflowRunCreateRequest,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
    runner: WorkflowRunner = Depends(get_workflow_runner),
):
    if not payload.submission_ids:
        raise HTTPException(status_code=400, detail="At least one submission must be provided")
    workflow = db.get(Workflow, payload.workflow_id)
    if workflow is None or workflow.archived:
        raise HTTPException(status_code=404, detail="Workflow not found")
    course = db.get(Course, workflow.course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    if not has_capability_and_owner(current_user, "run_workflow", course.instructor_id):
        raise HTTPException(status_code=403, detail="Not authorized to run this workflow")

    submissions = (
        db.query(Submission)
        .join(Submission.assignment)
        .filter(Submission.id.in_(payload.submission_ids))
        .all()
    )
    if len(submissions) != len(payload.submission_ids):
        raise HTTPException(status_code=404, detail="One or more submissions were not found")

    foreign_submissions = [s for s in submissions if s.assignment.course_id != course.id]
    if foreign_submissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="One or more submissions do not belong to the course this workflow is part of",
        )

    workflow_run = WorkflowRun(
        id=uuid4(),
        workflow_id=workflow.id,
        run_by=current_user.id,
        status=WorkflowRunStatus.pending,
        submissions=submissions,
        logs={"history": []},
        step_states=[],
        request_payload=payload.model_dump(mode="json", by_alias=True),
    )
    db.add(workflow_run)
    db.commit()
    db.refresh(workflow_run)

    runner.start_run(
        workflow_run_id=workflow_run.id,
        workflow_id=workflow.id,
        user_id=current_user.id,
        submission_ids=payload.submission_ids,
    )
    return _serialize_run(workflow_run)


@router.get("/", response_model=list[WorkflowRunRead])
def list_workflow_runs(
    course_id: UUID | None = None,
    assignment_id: UUID | None = Query(None, description="Filter runs by assignment"),
    workflow_id: UUID | None = Query(None, description="Filter runs by workflow"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    inferred_course_id = course_id
    if assignment_id:
        assignment = db.get(Assignment, assignment_id)
        if not assignment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
        if inferred_course_id and assignment.course_id != inferred_course_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assignment does not belong to the provided course")
        inferred_course_id = assignment.course_id
    if workflow_id:
        workflow = db.get(Workflow, workflow_id)
        if not workflow:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
        if inferred_course_id and workflow.course_id != inferred_course_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow does not belong to the provided course")
        inferred_course_id = inferred_course_id or workflow.course_id

    allowed_course_ids: list[UUID] | None = None
    if inferred_course_id:
        _assert_course_access(db, current_user, inferred_course_id)
    elif not has_capability(current_user, "update_any_course"):
        allowed_course_ids = [row[0] for row in db.query(Course.id).filter(Course.instructor_id == current_user.id).all()]
        if not allowed_course_ids:
            return []

    query = db.query(WorkflowRun).options(
        joinedload(WorkflowRun.submissions),
        joinedload(WorkflowRun.workflow),
        joinedload(WorkflowRun.runner),
    )
    if assignment_id:
        query = query.join(WorkflowRun.submissions).filter(Submission.assignment_id == assignment_id)
    if workflow_id:
        query = query.filter(WorkflowRun.workflow_id == workflow_id)
    if inferred_course_id:
        query = query.join(Workflow, WorkflowRun.workflow_id == Workflow.id).filter(Workflow.course_id == inferred_course_id)
    elif allowed_course_ids is not None:
        query = query.join(Workflow, WorkflowRun.workflow_id == Workflow.id).filter(Workflow.course_id.in_(allowed_course_ids))

    runs = query.order_by(WorkflowRun.started_at.desc()).distinct().offset(offset).limit(limit).all()
    return [_serialize_run(run) for run in runs]


@router.get("/{workflow_run_id}", response_model=WorkflowRunRead)
def get_workflow_run(
    workflow_run_id: UUID,
    db: Session = Depends(session_dependency),
    current_user: User = Depends(get_current_user),
):
    run = (
        db.query(WorkflowRun)
        .options(
            joinedload(WorkflowRun.submissions),
            joinedload(WorkflowRun.workflow),
            joinedload(WorkflowRun.runner),
        )
        .filter(WorkflowRun.id == workflow_run_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found")
    course_id = run.workflow.course_id if run.workflow else None
    if course_id:
        _assert_course_access(db, current_user, course_id)
    elif not has_capability(current_user, "update_any_course"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow run is missing its course relationship")
    return _serialize_run(run)


@router.get("/{workflow_run_id}/stream")
async def stream_workflow_run(
    workflow_run_id: UUID,
    request: Request,
    db: Session = Depends(session_dependency),
    broker: WorkflowRunEventBroker = Depends(get_workflow_event_broker),
):
    current_user = _current_user_from_stream_request(request, db)
    run = (
        db.query(WorkflowRun)
        .options(joinedload(WorkflowRun.workflow))
        .filter(WorkflowRun.id == workflow_run_id)
        .first()
    )
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found")
    if run.workflow is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workflow run is missing its workflow relationship")
    _assert_course_access(db, current_user, run.workflow.course_id)

    def _sse(event: str, data: dict) -> bytes:
        return format_sse_event(event=event, data_str=json.dumps(jsonable_encoder(data)))

    async def event_stream() -> AsyncIterable[bytes]:
        history = ((run.logs or {}).get("history", [])) if isinstance(run.logs, dict) else []
        for entry in history:
            yield _sse(entry.get("type", "log"), entry)
        subscription = await broker.subscribe(workflow_run_id)
        async with subscription:
            while True:
                if await request.is_disconnected():
                    return
                event = await subscription.get(timeout=15.0)
                if event is None:
                    with get_session() as poll_db:
                        latest = poll_db.get(WorkflowRun, workflow_run_id)
                        if latest and latest.status in {WorkflowRunStatus.success, WorkflowRunStatus.failure, WorkflowRunStatus.cancelled}:
                            yield _sse(
                                "end",
                                {
                                    "workflow_run_id": str(workflow_run_id),
                                    "status": latest.status,
                                    "finished_at": latest.finished_at,
                                },
                            )
                            return
                    continue
                yield _sse(event.get("type", "log"), event)
                if event.get("type") == "close":
                    with get_session() as poll_db:
                        latest = poll_db.get(WorkflowRun, workflow_run_id)
                    yield _sse(
                        "end",
                        {
                            "workflow_run_id": str(workflow_run_id),
                            "status": latest.status if latest else run.status,
                        },
                    )
                    return

    return EventSourceResponse(event_stream())


__all__ = ["router"]
