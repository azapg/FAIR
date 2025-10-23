import asyncio

from datetime import datetime
from typing import List
from uuid import UUID, uuid4


from fair_platform.backend.api.schema.submission import SubmissionBase
from fair_platform.backend.api.schema.workflow_run import WorkflowRunRead
from fair_platform.backend.data.database import get_session
from fair_platform.backend.data.models import (
    User,
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
    Submission,
    SubmissionStatus,
)
from fair_platform.sdk import get_plugin_object
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

        # TODO: omg i hate this, i think the best thing would be to save logs on error or completion only
        with get_session() as db:
            workflow_run = db.get(WorkflowRun, self.session_id)
            if workflow_run:
                current_logs = workflow_run.logs or {"history": []}
                history = list(current_logs.get("history", []))
                history.append(data)
                workflow_run.logs = {"history": history}

                try:
                    db.commit()
                    db.refresh(workflow_run)
                except Exception as e:
                    try:
                        self.logger.error(f"Failed to commit workflow run logs: {e}")
                    except Exception:
                        pass
                    try:
                        db.rollback()
                    except Exception:
                        pass

        if len(self.buffer) > 500:
            self.buffer.pop(0)


async def _update_workflow_run(
    db, session: Session, workflow_run: WorkflowRun, **updates
) -> WorkflowRun:
    payload = {"id": workflow_run.id}

    if "status" in updates:
        workflow_run.status = updates["status"]
    if "started_at" in updates:
        workflow_run.started_at = updates["started_at"]
    if "finished_at" in updates:
        workflow_run.finished_at = updates["finished_at"]
    db.commit()

    if "status" in updates:
        payload["status"] = workflow_run.status
    if "started_at" in updates:
        payload["started_at"] = workflow_run.started_at.isoformat()
    if "finished_at" in updates:
        payload["finished_at"] = workflow_run.finished_at.isoformat()

    await session.bus.emit(
        "update",
        {
            "object": "workflow_run",
            "type": "update",
            "payload": payload,
        },
    )
    return workflow_run


async def _update_submissions(
    db, session: Session, submissions: List[Submission], **updates
) -> List[Submission]:
    for sub in submissions:
        if "status" in updates:
            sub.status = updates["status"]
        if "official_run_id" in updates:
            sub.official_run_id = updates["official_run_id"]
    db.commit()

    payload_items = []
    for sub in submissions:
        item = {"id": sub.id}
        if "status" in updates:
            item["status"] = sub.status
        if "official_run_id" in updates:
            item["official_run_id"] = sub.official_run_id
        payload_items.append(item)

    await session.bus.emit(
        "update",
        {
            "object": "submissions",
            "type": "update",
            "payload": payload_items,
        },
    )
    return submissions


async def report_failure(
    session: Session,
    session_id: UUID,
    submission_ids: List[UUID],
    reason: str,
    log_message: str | None = None,
) -> int:
    if log_message:
        session.logger.error(log_message)
    with get_session() as db:
        workflow_run = db.get(WorkflowRun, session_id)
        if not workflow_run:
            await session.bus.emit("close", {"reason": reason})
            return -1

        await _update_workflow_run(
            db,
            session,
            workflow_run,
            status=WorkflowRunStatus.failure,
            finished_at=datetime.now(),
        )

        if submission_ids:
            submissions = (
                db.query(Submission).filter(Submission.id.in_(submission_ids)).all()
            )
            if submissions:
                await _update_submissions(
                    db,
                    session,
                    submissions,
                    status=SubmissionStatus.failure,
                )

    await session.bus.emit("close", {"reason": reason})
    return -1


class SessionManager:
    def __init__(self):
        self.sessions: dict[UUID, Session] = {}

    def create_session(
        self,
        workflow_id: UUID,
        submission_ids: List[UUID],
        user: User,
        parallelism: int = 10,
    ) -> WorkflowRunRead:
        with get_session() as db:
            workflow = db.get(Workflow, workflow_id)

            if not workflow:
                raise ValueError("Workflow not found")

            session_id = uuid4()
            task = asyncio.create_task(
                self._run_task(session_id, workflow, submission_ids, user, parallelism)
            )
            self.sessions[session_id] = Session(session_id, task)

            submissions = (
                db.query(Submission).filter(Submission.id.in_(submission_ids)).all()
            )

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

    async def _run_task(
        self,
        session_id: UUID,
        workflow: Workflow,
        submission_ids: List[UUID],
        user: User,
        parallelism: int = 10,
    ):
        session = self.sessions.get(session_id)

        if not session:
            return -1

        session.logger.log(
            "info",
            f"Starting session for workflow {workflow.name} with {len(submission_ids)} submissions",
        )

        with get_session() as db:
            workflow_run = db.get(WorkflowRun, session_id)
            if not workflow_run:
                await session.bus.emit(
                    "close", {"reason": "Workflow run not found in database"}
                )
                return -1

            await _update_workflow_run(
                db,
                session,
                workflow_run,
                status=WorkflowRunStatus.running,
                started_at=datetime.now(),
            )

            submissions = (
                db.query(Submission).filter(Submission.id.in_(submission_ids)).all()
            )
            if not submissions or len(submissions) == 0:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="No valid submissions found for this session",
                    log_message="No valid submissions found for this session",
                )

            await _update_submissions(
                db,
                session,
                submissions,
                status=SubmissionStatus.processing,
                official_run_id=workflow_run.id,
            )

            session.logger.info(f"Loaded {len(submissions)} submissions for processing")

        # Transcription
        if workflow.transcriber_plugin_id:
            session.logger.info("Starting transcription step")
            transcriber = get_plugin_object(workflow.transcriber_plugin_id)

            if not transcriber:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to missing transcriber plugin",
                    log_message="Transcriber plugin not found",
                )

            session.logger.debug(
                f"Using transcriber plugin: {workflow.transcriber_plugin_id}"
            )

            transcriber = transcriber(
                session.logger.get_child(workflow.transcriber_plugin_id)
            )
            transcriber.set_values(workflow.transcriber_settings or {})

            session.logger.debug(
                f"Transcriber initialized with settings {workflow.transcriber_settings}"
            )

            try:
                session.logger.debug("Beginning transcription...")
                transcriber.transcribe_batch(submissions)
            except Exception as e:
                session.logger.debug(f"Transcription failed: {e}")
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to transcription error",
                    log_message=f"Transcription failed: {e}",
                )

            session.logger.info("Transcription step completed")
        else:
            # TODO: This is temporary. I would like to support workflows without transcription in the future,
            #  but it requires rethinking the flow.
            return await report_failure(
                session,
                session_id,
                submission_ids,
                reason="Session failed due to missing transcription step",
                log_message="No transcription step found. Processing without transcription is not supported.",
            )

        session.logger.info("Session completed.")
        with get_session() as db:
            workflow_run = db.get(WorkflowRun, session_id)
            if not workflow_run:
                await session.bus.emit(
                    "close",
                    {"reason": "Workflow run not found in database at completion"},
                )
                return -1

            _ = await _update_workflow_run(
                db,
                session,
                workflow_run,
                status=WorkflowRunStatus.success,
                finished_at=datetime.now(),
            )

            submissions = (
                db.query(Submission).filter(Submission.id.in_(submission_ids)).all()
            )

            _ = await _update_submissions(
                db,
                session,
                submissions,
                status=SubmissionStatus.failure,
            )

        await session.bus.emit("close", {"reason": "Session completed"})
        return 0


session_manager = SessionManager()
