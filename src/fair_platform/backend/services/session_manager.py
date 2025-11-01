import asyncio
import inspect

from datetime import datetime
from typing import List, Tuple
from uuid import UUID, uuid4


from fair_platform.backend.api.schema.submission import SubmissionBase
from fair_platform.sdk import (
    GradeResult,
    Submitter as SDKSubmitter,
    Assignment as SDKAssignment,
    Artifact as SDKArtifact,
    Submission as SDKSubmission,
    TranscribedSubmission,
)
from fair_platform.backend.api.schema.workflow_run import WorkflowRunRead
from fair_platform.backend.data.database import get_session
from fair_platform.backend.data.models import (
    User,
    Submitter,
    Workflow,
    WorkflowRun,
    WorkflowRunStatus,
    Submission,
    SubmissionStatus,
)
from fair_platform.backend.data.models import SubmissionResult

from sqlalchemy.orm import joinedload
from fair_platform.sdk import get_plugin_object

from fair_platform.sdk.events import IndexedEventBus

from fair_platform.sdk.logger import SessionLogger


class Session:
    def __init__(self, session_id: UUID, task):
        self.session_id = session_id
        self.task = task
        self.buffer = []  # Circular buffer for logs (500 max entries)
        self.bus = IndexedEventBus()
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


async def _upsert_submission_result(
    db,
    session: Session,
    submission_id: UUID,
    workflow_run_id: UUID,
    **updates,
) -> SubmissionResult:
    """Create or update a SubmissionResult for a given submission + workflow run.

    Accepts fields: transcription, transcription_confidence, transcribed_at,
    score, feedback, grading_meta, graded_at.
    """
    result = (
        db.query(SubmissionResult)
        .filter(
            SubmissionResult.submission_id == submission_id,
            SubmissionResult.workflow_run_id == workflow_run_id,
        )
        .first()
    )

    if not result:
        result = SubmissionResult(
            submission_id=submission_id, workflow_run_id=workflow_run_id
        )
        db.add(result)

    # Set supported fields if provided
    for key in (
        "transcription",
        "transcription_confidence",
        "transcribed_at",
        "score",
        "feedback",
        "grading_meta",
        "graded_at",
    ):
        if key in updates:
            setattr(result, key, updates[key])

    db.commit()
    db.refresh(result)

    return result


async def report_failure(
    session: Session,
    session_id: UUID,
    submission_ids: List[UUID],
    reason: str,
    log_message: str | None = None,
) -> int:
    if log_message:
        await session.logger.error(log_message)
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

        await session.logger.info(
            f"Starting session for workflow {workflow.name} for {len(submission_ids)} submissions",
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

            updated_submissions = (
                db.query(Submission).filter(Submission.id.in_(submission_ids)).all()
            )
            if not updated_submissions or len(updated_submissions) == 0:
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
                updated_submissions,
                status=SubmissionStatus.processing,
                official_run_id=workflow_run.id,
            )

        # Transcription
        if workflow.transcriber_plugin_id:
            await session.logger.info("Starting transcription step")
            transcriber_cls = get_plugin_object(workflow.transcriber_plugin_id)

            if not transcriber_cls:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to missing transcriber plugin",
                    log_message="Transcriber plugin not found",
                )

            try:
                transcriber_instance = transcriber_cls(
                    session.logger.get_child(workflow.transcriber_plugin_id)
                )
            except Exception as e:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to transcriber plugin initialization error",
                    log_message=f"Transcriber plugin initialization error: {e}",
                )

            try:
                transcriber_instance.set_values(workflow.transcriber_settings or {})
            except Exception as e:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to transcriber configuration error",
                    log_message=f"Transcriber configuration error: {e}",
                )

            try:
                # TODO: this is so ugly. the only reason I made it this way is to have a nice SDK schema, but damn...
                with get_session() as db:
                    db_submissions = (
                        db.query(Submission)
                        .filter(Submission.id.in_(submission_ids))
                        .options(
                            joinedload(Submission.artifacts),
                            joinedload(Submission.assignment),
                        )
                        .all()
                    )

                    await _update_submissions(
                        db,
                        session,
                        db_submissions,
                        status=SubmissionStatus.transcribing,
                    )

                    submitter_ids = [s.submitter_id for s in db_submissions]
                    submitters = db.query(Submitter).filter(Submitter.id.in_(submitter_ids)).all()
                    submitter_map = {s.id: s for s in submitters}

                    sdk_submissions: List[SDKSubmission] = []
                    for sub in db_submissions:
                        submitter_obj = submitter_map.get(sub.submitter_id)
                        sdk_submitter = SDKSubmitter(
                            id=str(submitter_obj.id) if submitter_obj else "",
                            name=submitter_obj.name if submitter_obj else "",
                            email=str(submitter_obj.email) if submitter_obj and submitter_obj.email else "",
                        )

                        assign_obj = sub.assignment
                        # TODO: Score is a more complex object in the future, I am just using
                        # this because I set that in the SDK in the past for some reason
                        max_score = 0.0
                        try:
                            if assign_obj and assign_obj.max_grade is not None:
                                value = assign_obj.max_grade.get("value")
                                if isinstance(value, (int, float)):
                                    max_score = float(value)
                        except Exception:
                            max_score = 0.0

                        sdk_assignment = SDKAssignment(
                            id=str(assign_obj.id) if assign_obj else "",
                            title=assign_obj.title if assign_obj else "",
                            description=assign_obj.description
                            if assign_obj and assign_obj.description
                            else "",
                            deadline=assign_obj.deadline.isoformat()
                            if assign_obj and assign_obj.deadline
                            else "",
                            max_score=max_score,
                        )

                        sdk_artifacts = [
                            SDKArtifact(
                                title=a.title,
                                artifact_type=a.artifact_type,
                                mime=a.mime,
                                storage_path=a.storage_path,
                                storage_type=a.storage_type,
                                meta=a.meta,
                            )
                            for a in sub.artifacts
                        ]

                        sdk_submissions.append(
                            SDKSubmission(
                                id=str(sub.id),
                                submitter=sdk_submitter,
                                submitted_at=sub.submitted_at.isoformat()
                                if sub.submitted_at
                                else "",
                                assignment=sdk_assignment,
                                artifacts=sdk_artifacts,
                                meta={
                                    "status": sub.status.value
                                    if hasattr(sub.status, "value")
                                    else str(sub.status)
                                },
                            )
                        )

                semaphore = asyncio.Semaphore(parallelism)

                async def transcribe_wrapper(
                    submission: SDKSubmission,
                ) -> Tuple[SDKSubmission, TranscribedSubmission]:
                    async with semaphore:
                        if inspect.iscoroutinefunction(transcriber_instance.transcribe):
                            result = await transcriber_instance.transcribe(submission)
                        else:
                            loop = asyncio.get_running_loop()
                            result = await loop.run_in_executor(
                                None, transcriber_instance.transcribe, submission
                            )
                        return (submission, result)

                transcription_results = await asyncio.gather(
                    *[transcribe_wrapper(sub) for sub in sdk_submissions],
                    return_exceptions=True,
                )

                with get_session() as db:
                    updated_submissions = []
                    for res in transcription_results:
                        if isinstance(res, Exception):
                            sdk_sub = sdk_submissions[transcription_results.index(res)]
                            submitter = sdk_sub.submitter.name
                            db_sub = db.get(Submission, UUID(sdk_sub.id))
                            if not db_sub:
                                await session.logger.warning(
                                    f"Can't find {submitter}'s submission, skipping."
                                )
                                continue

                            await session.logger.error(
                                f"Transcription failed for {submitter}'s submission: {res}"
                            )

                            await _update_submissions(
                                db,
                                session,
                                [db_sub],
                                status=SubmissionStatus.failure,
                            )
                            continue

                        original, transcribed = res
                        sub_id = UUID(original.id)
                        db_submission = db.get(Submission, sub_id)
                        if not db_submission:
                            await session.logger.warning(
                                f"Can't find {original.submitter.name}'s submission, skipping."
                            )
                            continue
                        # Persist transcription result
                        await _upsert_submission_result(
                            db,
                            session,
                            submission_id=sub_id,
                            workflow_run_id=session_id,
                            transcription=transcribed.transcription,
                            transcription_confidence=transcribed.confidence,
                            transcribed_at=datetime.now(),
                        )

                        updated_submissions.append(db_submission)

                    if updated_submissions:
                        await _update_submissions(
                            db,
                            session,
                            updated_submissions,
                            status=SubmissionStatus.transcribed,
                        )

            except Exception as e:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to transcription error",
                    log_message=f"Transcription failed: {e}",
                )

            await session.logger.info("Transcription step completed")
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

        if workflow.grader_plugin_id:
            await session.logger.info("Starting grading step")
            grader_cls = get_plugin_object(workflow.grader_plugin_id)
            if not grader_cls:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to missing grader plugin",
                    log_message="Grader plugin not found",
                )

            try:
                grader_instance = grader_cls(
                    session.logger.get_child(workflow.grader_plugin_id)
                )
            except Exception as e:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to grader plugin initialization error",
                    log_message=f"Grader plugin initialization error: {e}",
                )

            try:
                grader_instance.set_values(workflow.grader_settings or {})
            except Exception as e:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to grader configuration error",
                    log_message=f"Grader configuration error: {e}",
                )

            try:
                valid_t_results = [
                    tr for tr in transcription_results if not isinstance(tr, Exception)
                ]

                db_subs = []
                with get_session() as db:
                    for result in valid_t_results:
                        db_sub = db.get(Submission, UUID(result[0].id))
                        if db_sub:
                            db_subs.append(db_sub)

                    await _update_submissions(
                        db,
                        session,
                        list(db_subs),
                        status=SubmissionStatus.grading,
                    )

                if not valid_t_results:
                    await session.logger.warning(
                        "No submissions to grade, skipping grading step"
                    )
                    grading_results = []
                else:
                    semaphore = asyncio.Semaphore(parallelism)

                    # I want to have a reference of the original and the transcribed result after grading,
                    # and because I can't pass them directly to asyncio.gather, I just wrap them here
                    async def grade_wrapper(
                        original: SDKSubmission,
                        transcribed_result: TranscribedSubmission,
                    ) -> Tuple[SDKSubmission, TranscribedSubmission, GradeResult]:
                        async with semaphore:
                            if inspect.iscoroutinefunction(grader_instance.grade):
                                result = await grader_instance.grade(
                                    transcribed_result, original
                                )
                            else:
                                loop = asyncio.get_running_loop()
                                result = await loop.run_in_executor(
                                    None,
                                    grader_instance.grade,
                                    transcribed_result,
                                    original,
                                )
                        return (original, transcribed_result, result)

                    grading_results = await asyncio.gather(
                        *[grade_wrapper(*tr) for tr in valid_t_results],
                        return_exceptions=True,
                    )

                    try:
                        with get_session() as db:
                            to_update_success = []
                            to_update_failure = []

                            for idx, res in enumerate(grading_results):
                                sdk_sub = valid_t_results[idx][0]
                                submitter = sdk_sub.submitter.name
                                if isinstance(res, Exception):
                                    sub_id = UUID(valid_t_results[idx][0].id)
                                    db_sub = db.get(Submission, sub_id)
                                    if db_sub:
                                        await session.logger.error(
                                            f"Grading failed for {submitter}'s submission: {res}"
                                        )
                                        to_update_failure.append(db_sub)
                                    else:
                                        await session.logger.warning(
                                            f"Can't find {submitter}'s submission, skipping."
                                        )
                                    continue

                                original, _, grade_result = res
                                original_id = UUID(original.id)

                                db_sub = db.get(Submission, original_id)
                                if not db_sub:
                                    await session.logger.warning(
                                        f"Can't find {original.submitter.name}'s submission, skipping."
                                    )
                                    continue

                                # Persist grade result (upsert on existing submission_result)
                                await _upsert_submission_result(
                                    db,
                                    session,
                                    submission_id=original_id,
                                    workflow_run_id=session_id,
                                    score=grade_result.score,
                                    feedback=grade_result.feedback,
                                    grading_meta=grade_result.meta,
                                    graded_at=datetime.now(),
                                )

                                to_update_success.append(db_sub)

                            if to_update_failure:
                                await _update_submissions(
                                    db,
                                    session,
                                    to_update_failure,
                                    status=SubmissionStatus.failure,
                                )

                            if to_update_success:
                                await _update_submissions(
                                    db,
                                    session,
                                    to_update_success,
                                    status=SubmissionStatus.graded,
                                )
                    except Exception as e:
                        return await report_failure(
                            session,
                            session_id,
                            submission_ids,
                            reason="Session failed while persisting grading results",
                            log_message=f"Failed to persist grading results: {e}",
                        )

            except Exception as e:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to grading error",
                    log_message=f"Grading failed: {e}",
                )

            await session.logger.info("Grading step completed")

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

        await session.bus.emit("close", {"reason": "Session completed"})
        return 0


session_manager = SessionManager()
