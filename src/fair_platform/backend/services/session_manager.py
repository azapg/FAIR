import asyncio
from typing import List
from uuid import UUID, uuid4

from fair_platform.backend.data.database import get_session
from fair_platform.backend.data.models import User, Workflow, Plugin, WorkflowRun, WorkflowRunStatus, Submission
from fair_platform.sdk import get_plugin_object
from fair_platform.sdk.events import EventBus
from fair_platform.sdk.logger import SessionLogger


class Session:
    def __init__(self, session_id: UUID, task):
        self.session_id = session_id
        self.task = task
        self.buffer = []  # Circular buffer for logs (500 max entries)
        # TODO: I think for now I will create a per-session bus, but it could also be a session manager global bus?
        self.bus = EventBus()
        self.bus.on(f"session:{session_id.hex}:log", self.add_log)
        self.logger = SessionLogger(session_id.hex, self.bus)

    def add_log(self, data: dict):
        self.buffer.append(data)
        if len(self.buffer) > 500:
            self.buffer.pop(0)


class SessionManager:
    def __init__(self):
        self.sessions: dict[UUID, Session] = {}

    def create_session(self, workflow_id: UUID, submission_ids: List[UUID], user: User, parallelism: int = 10) -> UUID:
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

        return session_id

    async def _run_task(self, session_id: UUID, workflow: Workflow, submission_ids: List[UUID], user: User, parallelism: int = 10):
        session = self.sessions[session_id]
        session.logger.log("info", f"Starting session for workflow {workflow.name} with {len(submission_ids)} submissions")
        try:
            if workflow.transcriber_plugin_id:
                with get_session() as db:
                    plugin = db.query(Plugin).filter(Plugin.id == workflow.transcriber_plugin_id).first()

                transcription = None

                if not plugin:
                    raise ValueError("Transcriber plugin not found")

                plugin_class = get_plugin_object(plugin.name) # TODO: This should look for a plugin with a specific id and hash

                if not plugin_class:
                    raise ValueError("Transcriber plugin class not found")

                transcriber = plugin_class(session.logger.get_child(plugin_id=plugin.id))
                transcriber.set_values(workflow.transcriber_settings or {})
                session.logger.log("info", f"Initialized transcriber plugin {plugin.name}")

                await asyncio.sleep(10)
                session.logger.log("info", f"Transcription completed")

            if workflow.grader_plugin_id:
                session.logger.log("info", f"Starting grading step with plugin {workflow.grader_plugin_id}")
                await asyncio.sleep(10)
                session.logger.log("info", f"Grading completed")

            if workflow.validator_plugin_id:
                session.logger.log("info", f"Starting validation step")
                await asyncio.sleep(10)
            return 0
        except Exception as e:
            raise
        finally:
            pass

session_manager = SessionManager()