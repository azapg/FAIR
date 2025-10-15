import asyncio
from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from fair_platform.backend.api.schema.submission import SubmissionBase
from fair_platform.backend.api.schema.workflow_run import WorkflowRunRead
from fair_platform.backend.data.database import get_session
from fair_platform.backend.data.models import User, Workflow,  WorkflowRun, WorkflowRunStatus, Submission, SubmissionStatus
from fair_platform.sdk.events import EventBus
from fair_platform.sdk.logger import SessionLogger


class Session:
    def __init__(self, session_id: UUID, task):
        self.session_id = session_id
        self.task = task
        self.buffer = []  # Circular buffer for logs (500 max entries)
        self.bus = EventBus()
        self.bus.on("log", self.add_log)
        self.bus.on("close", self.add_log)
        self.bus.on("update", self.add_log)
        self.logger = SessionLogger(session_id.hex, self.bus)

    def add_log(self, data: dict):
        self.buffer.append(data)
        if len(self.buffer) > 500:
            self.buffer.pop(0)


class SessionManager:
    def __init__(self):
        self.sessions: dict[UUID, Session] = {}

    def create_session(self, workflow_id: UUID, submission_ids: List[UUID], user: User, parallelism: int = 10) -> WorkflowRunRead:
        with get_session() as db:
            workflow = db.get(Workflow, workflow_id)

            if not workflow:
                raise ValueError("Workflow not found")

            session_id = uuid4()
            task = asyncio.create_task(self._run_task(session_id, workflow, submission_ids, user, parallelism))
            self.sessions[session_id] = Session(session_id, task)

            submissions = db.query(Submission).filter(Submission.id.in_(submission_ids)).all()

            workflow_run = WorkflowRun(
                id=session_id,
                run_by=user.id,
                workflow_id=workflow.id,
                status=WorkflowRunStatus.pending,
                submissions=submissions,
            )
            db.add(workflow_run)
            db.commit()
            db.refresh(workflow_run)

        # TODO: Just noticed that this doesn't hold a reference to the workflow id
        return WorkflowRunRead(
            id=workflow_run.id,
            run_by=workflow_run.run_by,
            status=workflow_run.status,
            started_at=workflow_run.started_at,
            finished_at=workflow_run.finished_at,
            logs=workflow_run.logs,
            submissions=[SubmissionBase.model_validate(sub) for sub in submissions],
        )

    async def _run_task(self, session_id: UUID, workflow: Workflow, submission_ids: List[UUID], user: User, parallelism: int = 10):
        session = self.sessions[session_id]
        session.logger.log("info", f"Starting session for workflow {workflow.name} with {len(submission_ids)} submissions")

        with get_session() as db:
            workflow_run = db.get(WorkflowRun, session_id)
            if not workflow_run:
                session.logger.error("Workflow run not found in database")
                return -1
            workflow_run.status = WorkflowRunStatus.running
            workflow_run.started_at = datetime.now()
            db.commit()

            await session.bus.emit('update', {
                "object": "workflow_run",
                "type": "update",
                "payload": {"id": workflow_run.id, "status": workflow_run.status, "started_at": workflow_run.started_at.isoformat()},
            })

            submissions = db.query(Submission).filter(Submission.id.in_(submission_ids)).all()
            if not submissions or len(submissions) == 0:
                session.logger.error("No valid submissions found for this session")
                workflow_run.status = WorkflowRunStatus.failure
                workflow_run.finished_at = datetime.now()
                db.commit()
                await session.bus.emit('update', {
                    "object": "workflow_run",
                    "type": "update",
                    "payload": {"id": workflow_run.id, "status": workflow_run.status, "finished_at": workflow_run.finished_at.isoformat()},
                })
                return -1

            for submission in submissions:
                submission.status = SubmissionStatus.processing
                submission.official_run_id = workflow_run.id
            db.commit()

            await session.bus.emit('update', {
                "object": "submissions",
                "type": "update",
                "payload": [{"id": sub.id, "status": sub.status, "official_run_id": sub.official_run_id} for sub in submissions],
            })

            session.logger.info(f"Loaded {len(submissions)} submissions for processing")

        session.logger.warning("Plugin execution is not yet implemented.")
        await asyncio.sleep(10)
        session.logger.info("Session completed.")
        with get_session() as db:
            workflow_run = db.get(WorkflowRun, session_id)
            if not workflow_run:
                session.logger.error("Workflow run not found in database at completion")
                workflow_run.status = WorkflowRunStatus.failure
                db.commit()
                return -1

            workflow_run.status = WorkflowRunStatus.success
            workflow_run.finished_at = datetime.now()
            db.commit()

            await session.bus.emit('update', {
                "object": "workflow_run",
                "type": "update",
                "payload": {"id": workflow_run.id, "status": workflow_run.status, "finished_at": workflow_run.finished_at.isoformat() },
            })

            submissions = db.query(Submission).filter(Submission.id.in_(submission_ids)).all()

            for submission in submissions:
                submission.status = SubmissionStatus.failure

            await session.bus.emit('update', {
                "object": "submissions",
                "type": "update",
                "payload": [{"id": sub.id, "status": sub.status} for sub in submissions],
            })

            db.commit()

        await session.bus.emit('close', {"reason": "Session completed"})
        return 0

session_manager = SessionManager()