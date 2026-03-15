from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import joinedload

from fair_platform.backend.api.schema.workflow import WorkflowStep
from fair_platform.backend.api.schema.workflow_run import WorkflowRunRead, WorkflowRunStepState
from fair_platform.backend.data.database import get_session
from fair_platform.backend.data.models import (
    Submission,
    SubmissionResult,
    SubmissionStatus,
    User,
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
)
from fair_platform.backend.services.job_queue import JobMessage, JobQueue, JobStatus
from fair_platform.backend.services.settings_validator import (
    CorruptedSettingsSchemaError,
    RuntimeSettingsValidationError,
    validate_and_hydrate_runtime_settings,
)
from fair_platform.backend.services.submission_manager import SubmissionManager


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _history_entry(event_type: str, level: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ts": _utc_now().isoformat(),
        "type": event_type,
        "level": level,
        "payload": payload,
    }


def _normalize_update_event(
    step_ctx: "StepContext",
    workflow_run_id: UUID,
    update_event: str,
    update_payload: dict[str, Any],
) -> tuple[str, str, dict[str, Any]]:
    base_payload = {
        "workflow_run_id": str(workflow_run_id),
        "step_id": step_ctx.step.id,
        "step_index": step_ctx.index,
        "plugin_type": step_ctx.step.plugin.plugin_type,
        "plugin_id": step_ctx.step.plugin.plugin_id,
        "job_id": step_ctx.job_id,
    }

    if update_event == "log":
        return (
            "log",
            str(update_payload.get("level") or "info"),
            {
                **base_payload,
                **update_payload,
                "message": update_payload.get("message") or update_payload.get("output") or "",
            },
        )
    if update_event == "progress":
        percent = update_payload.get("percent")
        progress_message = update_payload.get("message") or (
            f"{step_ctx.step.plugin.plugin_type.capitalize()} step progress: {percent}%"
            if percent is not None
            else f"{step_ctx.step.plugin.plugin_type.capitalize()} step running"
        )
        return (
            "log",
            "info",
            {
                **base_payload,
                **update_payload,
                "message": progress_message,
            },
        )
    if update_event == "result":
        return (
            "result",
            "info",
            {
                **base_payload,
                **update_payload,
                "message": f"Completed {step_ctx.step.plugin.plugin_type} step",
            },
        )
    if update_event == "error":
        return (
            "error",
            "error",
            {
                **base_payload,
                **update_payload,
                "message": update_payload.get("message") or update_payload.get("error") or "Step failed",
            },
        )
    if update_event == "submission_result":
        submission_id = update_payload.get("submission_id") or update_payload.get("submissionId")
        item = update_payload.get("data", {})
        return (
            "log",
            "info",
            {
                **base_payload,
                **update_payload,
                "message": f"Completed {step_ctx.step.plugin.plugin_type} for submission {submission_id}",
                "submission_id": submission_id,
                "submission_result": item,
            },
        )
    return (
        update_event,
        "info",
        {
            **base_payload,
            **update_payload,
        },
    )


def _step_start_status(plugin_type: str) -> SubmissionStatus | None:
    if plugin_type == "transcriber":
        return SubmissionStatus.transcribing
    if plugin_type == "grader":
        return SubmissionStatus.grading
    if plugin_type == "reviewer":
        return SubmissionStatus.processing
    return None


class WorkflowRunSubscription:
    def __init__(self, queue: asyncio.Queue[dict[str, Any]], detach):
        self._queue = queue
        self._detach = detach

    async def get(self, timeout: float | None = None) -> dict[str, Any] | None:
        try:
            if timeout is None:
                return await self._queue.get()
            return await asyncio.wait_for(self._queue.get(), timeout=timeout)
        except TimeoutError:
            return None

    async def close(self) -> None:
        self._detach(self._queue)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_ignored):
        await self.close()


class WorkflowRunEventBroker:
    def __init__(self):
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}

    async def publish(self, run_id: UUID | str, event: dict[str, Any]) -> None:
        key = str(run_id)
        for queue in self._subscribers.get(key, set()):
            await queue.put(event)

    async def subscribe(self, run_id: UUID | str) -> WorkflowRunSubscription:
        key = str(run_id)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._subscribers.setdefault(key, set()).add(queue)
        return WorkflowRunSubscription(queue, lambda q: self._detach(key, q))

    def _detach(self, run_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        subscribers = self._subscribers.get(run_id)
        if not subscribers:
            return
        subscribers.discard(queue)
        if not subscribers:
            self._subscribers.pop(run_id, None)


@dataclass
class StepContext:
    index: int
    step: WorkflowStep
    job_id: str


class WorkflowRunner:
    def __init__(self, job_queue: JobQueue, event_broker: WorkflowRunEventBroker):
        self._job_queue = job_queue
        self._broker = event_broker
        self._tasks: dict[str, asyncio.Task[None]] = {}

    def start_run(
        self,
        workflow_run_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
        submission_ids: list[UUID],
    ) -> None:
        task = asyncio.create_task(
            self._run_pipeline(workflow_run_id, workflow_id, user_id, submission_ids)
        )
        self._tasks[str(workflow_run_id)] = task

    async def _run_pipeline(
        self,
        workflow_run_id: UUID,
        workflow_id: UUID,
        user_id: UUID,
        submission_ids: list[UUID],
    ) -> None:
        current_step_ctx: StepContext | None = None
        with get_session() as db:
            workflow = db.query(Workflow).filter(Workflow.id == workflow_id).first()
            workflow_run = db.get(WorkflowRun, workflow_run_id)
            user = db.get(User, user_id)
            submissions = (
                db.query(Submission)
                .options(joinedload(Submission.artifacts))
                .filter(Submission.id.in_(submission_ids))
                .all()
            )
            if not workflow or not workflow_run or not user:
                return

            steps = [WorkflowStep.model_validate(step) for step in (workflow.steps or [])]
            workflow_run.status = WorkflowRunStatus.running
            workflow_run.started_at = _utc_now()
            workflow_run.logs = workflow_run.logs or {"history": []}
            workflow_run.step_states = workflow_run.step_states or []
            db.add(workflow_run)
            db.commit()

        state_by_submission: dict[str, dict[str, Any]] = {
            str(submission_id): {} for submission_id in submission_ids
        }
        try:
            for index, step in enumerate(steps):
                step_ctx = StepContext(index=index, step=step, job_id=str(uuid4()))
                current_step_ctx = step_ctx
                await self._append_event(
                    workflow_run_id,
                    "log",
                    "info",
                    {
                        "message": f"Starting {step.plugin.plugin_type} step",
                        "step_id": step.id,
                        "step_index": index,
                        "plugin_id": step.plugin.plugin_id,
                        "job_id": step_ctx.job_id,
                    },
                )
                await self._set_step_state(
                    workflow_run_id,
                    step_ctx,
                    status="queued",
                    result=None,
                    error=None,
                )
                await self._mark_step_started(workflow_run_id, submission_ids, step.plugin.plugin_type)
                request_payload = self._build_step_request(
                    workflow_run_id, step_ctx, submissions, state_by_submission
                )
                await self._job_queue.enqueue(
                    JobMessage(
                        job_id=step_ctx.job_id,
                        target=step.plugin.extension_id,
                        payload={
                            "action": step.plugin.action,
                            "params": request_payload,
                            "meta": {
                                "plugin_id": step.plugin.plugin_id,
                                "plugin_type": step.plugin.plugin_type,
                            },
                        },
                        metadata={
                            "workflow_run_id": str(workflow_run_id),
                            "step_id": step.id,
                            "step_index": index,
                        },
                    )
                )
                await self._job_queue.set_state(
                    step_ctx.job_id,
                    JobStatus.QUEUED,
                    details={
                        "target": step.plugin.extension_id,
                        "action": step.plugin.action,
                        "owner_user_id": str(user_id),
                        "owner_extension_id": step.plugin.extension_id,
                        "workflow_run_id": str(workflow_run_id),
                        "step_id": step.id,
                        "step_index": index,
                    },
                )
                result = await self._consume_step(
                    workflow_run_id,
                    step_ctx,
                    state_by_submission,
                )
                self._merge_results(step.plugin.plugin_type, result, state_by_submission)
                await self._persist_submission_results(workflow_run_id, result)
                current_step_ctx = None

            with get_session() as db:
                workflow_run = db.get(WorkflowRun, workflow_run_id)
                if workflow_run is not None:
                    workflow_run.status = WorkflowRunStatus.success
                    workflow_run.finished_at = _utc_now()
                    db.add(workflow_run)
                    db.commit()
            await self._append_event(
                workflow_run_id,
                "close",
                "info",
                {"reason": "completed"},
            )
        except Exception as exc:
            if current_step_ctx is not None:
                await self._set_step_state(
                    workflow_run_id,
                    current_step_ctx,
                    status="failed",
                    result=None,
                    error=str(exc),
                )
            with get_session() as db:
                workflow_run = db.get(WorkflowRun, workflow_run_id)
                if workflow_run is not None:
                    workflow_run.status = WorkflowRunStatus.failure
                    workflow_run.finished_at = _utc_now()
                    db.add(workflow_run)
                    db.commit()
            await self._append_event(
                workflow_run_id,
                "error",
                "error",
                {"message": str(exc)},
            )
            await self._append_event(
                workflow_run_id,
                "close",
                "error",
                {"reason": "failed"},
            )
        finally:
            self._tasks.pop(str(workflow_run_id), None)

    async def _mark_step_started(
        self,
        workflow_run_id: UUID,
        submission_ids: list[UUID],
        plugin_type: str,
    ) -> None:
        next_status = _step_start_status(plugin_type)
        if next_status is None:
            return
        changed = False
        with get_session() as db:
            manager = SubmissionManager(db)
            submissions = (
                db.query(Submission)
                .filter(Submission.id.in_(submission_ids))
                .all()
            )
            for submission in submissions:
                previous_status = submission.status
                if previous_status == next_status:
                    continue
                submission.status = next_status
                manager.log_status_transition(
                    submission_id=submission.id,
                    from_status=previous_status,
                    to_status=next_status,
                    workflow_run_id=workflow_run_id,
                    reason=f"{plugin_type}_started",
                )
                changed = True
            if changed:
                db.commit()
        if changed:
            await self._append_event(
                workflow_run_id,
                "update",
                "info",
                {"object": "submissions", "action": "refresh"},
            )

    def _build_step_request(
        self,
        workflow_run_id: UUID,
        step_ctx: StepContext,
        submissions: list[Submission],
        state_by_submission: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        try:
            hydrated_settings = validate_and_hydrate_runtime_settings(
                plugin_id=step_ctx.step.plugin.plugin_id,
                settings_schema=step_ctx.step.plugin.settings_schema,
                incoming_settings=step_ctx.step.settings,
            )
        except RuntimeSettingsValidationError as exc:
            raise ValueError(
                f"Settings validation failed for plugin '{exc.plugin_id}': field '{exc.field}' {exc.reason}"
            ) from exc
        except CorruptedSettingsSchemaError as exc:
            raise ValueError(
                f"Cannot execute workflow: plugin '{exc.plugin_id}' has corrupted settings_schema"
            ) from exc

        items = []
        for submission in submissions:
            items.append(
                {
                    "submission_id": str(submission.id),
                    "assignment_id": str(submission.assignment_id),
                    "status": submission.status,
                    "artifacts": [
                        {
                            "artifact_id": str(artifact.id),
                            "title": artifact.title,
                            "mime": artifact.mime,
                            "kind": artifact.artifact_type,
                        }
                        for artifact in submission.artifacts
                    ],
                    "state": state_by_submission.get(str(submission.id), {}),
                    "metadata": {},
                }
            )
        return {
            "workflow_run_id": str(workflow_run_id),
            "step_id": step_ctx.step.id,
            "step_index": step_ctx.index,
            "plugin": step_ctx.step.plugin.model_dump(by_alias=True, mode="json"),
            "settings": hydrated_settings,
            "submissions": items,
            "metadata": {},
        }

    async def _consume_step(
        self,
        workflow_run_id: UUID,
        step_ctx: StepContext,
        state_by_submission: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        subscription = await self._job_queue.subscribe_updates(step_ctx.job_id)
        result_payload: dict[str, Any] = {}
        partial_results: dict[str, dict[str, Any]] = {}
        async with subscription:
            while True:
                update = await subscription.get(timeout=1.0)
                state = await self._job_queue.get_state(step_ctx.job_id)
                if update is not None:
                    event_type, level, payload = _normalize_update_event(
                        step_ctx,
                        workflow_run_id,
                        update.event,
                        update.payload,
                    )
                    await self._append_event(workflow_run_id, event_type, level, payload)
                    if update.event in {"log", "progress", "result", "submission_result"}:
                        await self._set_step_state(
                            workflow_run_id,
                            step_ctx,
                            status="running",
                            result=result_payload or {"results": list(partial_results.values())} or None,
                            error=None,
                        )
                    if update.event == "submission_result":
                        submission_id = update.payload.get("submission_id") or update.payload.get("submissionId")
                        if submission_id:
                            item = {
                                "submission_id": str(submission_id),
                                **(update.payload.get("data") or {}),
                            }
                            partial_results[str(submission_id)] = item
                            partial_payload = {
                                "plugin_type": step_ctx.step.plugin.plugin_type,
                                "results": [item],
                            }
                            self._merge_results(
                                step_ctx.step.plugin.plugin_type,
                                partial_payload,
                                state_by_submission,
                            )
                            await self._persist_submission_results(workflow_run_id, partial_payload)
                    if update.event == "result":
                        result_payload = update.payload.get("data", {})
                        if partial_results:
                            merged_results = {
                                str(item.get("submission_id") or item.get("submissionId")): item
                                for item in result_payload.get("results", [])
                                if item.get("submission_id") or item.get("submissionId")
                            }
                            merged_results = {**partial_results, **merged_results}
                            result_payload["plugin_type"] = (
                                result_payload.get("plugin_type")
                                or step_ctx.step.plugin.plugin_type
                            )
                            result_payload["results"] = list(merged_results.values())
                    if update.event == "error":
                        await self._set_step_state(
                            workflow_run_id,
                            step_ctx,
                            status="failed",
                            result=result_payload or None,
                            error=update.payload.get("error"),
                        )
                if state and state.status in {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED}:
                    if state.status != JobStatus.COMPLETED:
                        raise RuntimeError(state.details.get("error") or f"Step {step_ctx.step.id} failed")
                    if not result_payload and partial_results:
                        result_payload = {
                            "plugin_type": step_ctx.step.plugin.plugin_type,
                            "results": list(partial_results.values()),
                            "metadata": {},
                        }
                    await self._set_step_state(
                        workflow_run_id,
                        step_ctx,
                        status="completed",
                        result=result_payload,
                        error=None,
                    )
                    return result_payload

    async def _append_event(self, workflow_run_id: UUID, event_type: str, level: str, payload: dict[str, Any]) -> None:
        entry = _history_entry(event_type, level, payload)
        with get_session() as db:
            workflow_run = db.get(WorkflowRun, workflow_run_id)
            if workflow_run is not None:
                logs = workflow_run.logs or {"history": []}
                history = list(logs.get("history", []))
                entry["index"] = len(history)
                history.append(entry)
                workflow_run.logs = {"history": history}
                db.add(workflow_run)
                db.commit()
        await self._broker.publish(workflow_run_id, entry)

    async def _set_step_state(
        self,
        workflow_run_id: UUID,
        step_ctx: StepContext,
        *,
        status: str,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> None:
        with get_session() as db:
            workflow_run = db.get(WorkflowRun, workflow_run_id)
            if workflow_run is None:
                return
            step_states = list(workflow_run.step_states or [])
            next_state = WorkflowRunStepState(
                step_id=step_ctx.step.id,
                step_index=step_ctx.index,
                plugin_id=step_ctx.step.plugin.plugin_id,
                plugin_type=step_ctx.step.plugin.plugin_type,
                extension_id=step_ctx.step.plugin.extension_id,
                status=status,
                job_id=step_ctx.job_id,
                result=result,
                error=error,
            ).model_dump(mode="json")
            step_states = [state for state in step_states if state.get("step_id") != step_ctx.step.id]
            step_states.append(next_state)
            step_states.sort(key=lambda item: item.get("step_index", 0))
            workflow_run.step_states = step_states
            db.add(workflow_run)
            db.commit()

    def _merge_results(
        self,
        plugin_type: str,
        result: dict[str, Any],
        state_by_submission: dict[str, dict[str, Any]],
    ) -> None:
        for item in result.get("results", []):
            submission_id = str(item.get("submission_id") or item.get("submissionId") or "")
            if not submission_id:
                continue
            state = state_by_submission.setdefault(submission_id, {})
            if plugin_type == "transcriber":
                state["transcription"] = item.get("transcription")
                state["transcription_metadata"] = item.get("metadata", {})
            elif plugin_type == "grader":
                state["grade"] = item.get("grade")
                state["feedback"] = item.get("feedback")
                state["grading_metadata"] = item.get("metadata", {})
            elif plugin_type == "reviewer":
                state["review_comments"] = item.get("comments", [])
                state["review_flags"] = item.get("flags", [])
                state["review_metadata"] = item.get("metadata", {})

    async def _persist_submission_results(self, workflow_run_id: UUID, result: dict[str, Any]) -> None:
        plugin_type = result.get("plugin_type")
        if not plugin_type:
            return
        changed = False
        with get_session() as db:
            manager = SubmissionManager(db)
            for item in result.get("results", []):
                submission_id = item.get("submission_id") or item.get("submissionId")
                if not submission_id:
                    continue
                submission_uuid = UUID(str(submission_id))
                submission = db.get(Submission, submission_uuid)
                if submission is None:
                    continue
                row = (
                    db.query(SubmissionResult)
                    .filter(
                        SubmissionResult.submission_id == submission_uuid,
                        SubmissionResult.workflow_run_id == workflow_run_id,
                    )
                    .first()
                )
                if row is None:
                    row = SubmissionResult(
                        submission_id=submission_uuid,
                        workflow_run_id=workflow_run_id,
                    )
                    db.add(row)
                if plugin_type == "transcriber":
                    row.transcription = item.get("transcription")
                    row.transcribed_at = _utc_now()
                    row.grading_meta = {
                        **(row.grading_meta or {}),
                        "transcription_metadata": item.get("metadata", {}),
                    }
                    previous_status = submission.status
                    submission.status = SubmissionStatus.transcribed
                    manager.log_status_transition(
                        submission_id=submission.id,
                        from_status=previous_status,
                        to_status=submission.status,
                        workflow_run_id=workflow_run_id,
                        reason="transcription_completed",
                    )
                    changed = True
                elif plugin_type == "grader":
                    row.score = item.get("grade")
                    row.feedback = item.get("feedback")
                    row.graded_at = _utc_now()
                    row.grading_meta = {
                        **(row.grading_meta or {}),
                        "grading_metadata": item.get("metadata", {}),
                    }
                    if item.get("grade") is not None or item.get("feedback") is not None:
                        manager.record_ai_result(
                            submission_id=submission.id,
                            score=float(item.get("grade")) if item.get("grade") is not None else 0.0,
                            feedback=item.get("feedback") or "",
                            workflow_run_id=workflow_run_id,
                        )
                    previous_status = submission.status
                    submission.status = SubmissionStatus.graded
                    manager.log_status_transition(
                        submission_id=submission.id,
                        from_status=previous_status,
                        to_status=submission.status,
                        workflow_run_id=workflow_run_id,
                        reason="grading_completed",
                    )
                    changed = True
                elif plugin_type == "reviewer":
                    row.grading_meta = {
                        **(row.grading_meta or {}),
                        "review": {
                            "comments": item.get("comments", []),
                            "flags": item.get("flags", []),
                            "metadata": item.get("metadata", {}),
                        },
                    }
                    previous_status = submission.status
                    flags = item.get("flags", []) or []
                    if flags:
                        submission.status = SubmissionStatus.needs_review
                    elif submission.draft_score is not None or submission.draft_feedback is not None:
                        submission.status = SubmissionStatus.graded
                    elif row.transcription:
                        submission.status = SubmissionStatus.transcribed
                    else:
                        submission.status = SubmissionStatus.submitted
                    manager.log_status_transition(
                        submission_id=submission.id,
                        from_status=previous_status,
                        to_status=submission.status,
                        workflow_run_id=workflow_run_id,
                        reason="review_completed",
                    )
                    changed = True
            db.commit()
        if changed:
            await self._append_event(
                workflow_run_id,
                "update",
                "info",
                {"object": "submissions", "action": "refresh"},
            )

    def serialize_run(self, workflow_run_id: UUID) -> WorkflowRunRead:
        with get_session() as db:
            run = (
                db.query(WorkflowRun)
                .options(
                    joinedload(WorkflowRun.submissions),
                    joinedload(WorkflowRun.runner),
                )
                .filter(WorkflowRun.id == workflow_run_id)
                .first()
            )
            if run is None:
                raise ValueError("Workflow run not found")
            return WorkflowRunRead(
                id=run.id,
                workflow_id=run.workflow_id,
                runner=run.runner,
                status=run.status,
                started_at=run.started_at,
                finished_at=run.finished_at,
                logs=run.logs,
                submissions=run.submissions,
                step_states=[WorkflowRunStepState.model_validate(item) for item in (run.step_states or [])],
                request_payload=run.request_payload,
            )


__all__ = ["WorkflowRunEventBroker", "WorkflowRunner"]
