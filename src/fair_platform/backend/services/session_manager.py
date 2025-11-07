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
from fair_platform.sdk import (
    TranscriptionPlugin,
    GradePlugin,
    ValidationPlugin,
    ValidationResult,
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


def is_method_overridden(instance, method_name: str, base_class) -> bool:
    """Check if a method was overridden in the instance's class."""
    instance_method = getattr(type(instance), method_name, None)
    base_method = getattr(base_class, method_name, None)
    if instance_method is None or base_method is None:
        return False
    return instance_method != base_method


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
            await session.logger.info("Starting transcription step...")
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

                use_batch_transcribe = is_method_overridden(
                    transcriber_instance, "transcribe_batch", TranscriptionPlugin
                )

                # We'll reuse this variable after the step
                transcription_results: List[
                    Tuple[SDKSubmission, TranscribedSubmission]
                ] = []

                if use_batch_transcribe:
                    await session.logger.info(
                        "Using batch transcription. Parallelism setting will be ignored."
                    )
                    # Call batch method with sync/async support
                    if inspect.iscoroutinefunction(
                        transcriber_instance.transcribe_batch
                    ):
                        batch_results = await transcriber_instance.transcribe_batch(
                            sdk_submissions
                        )
                    else:
                        loop = asyncio.get_running_loop()
                        batch_results = await loop.run_in_executor(
                            None,
                            transcriber_instance.transcribe_batch,
                            sdk_submissions,
                        )

                    if not isinstance(batch_results, list) or len(batch_results) != len(
                        sdk_submissions
                    ):
                        raise RuntimeError(
                            "Batch transcription returned unexpected result length"
                        )

                    with get_session() as db:
                        to_update: List[Submission] = []
                        for idx, tr in enumerate(batch_results):
                            original = sdk_submissions[idx]
                            sub_id = UUID(original.id)
                            db_submission = db.get(Submission, sub_id)
                            if not db_submission:
                                await session.logger.warning(
                                    f"Can't find {original.submitter.name}'s submission, skipping."
                                )
                                continue
                            await _upsert_submission_result(
                                db,
                                session,
                                submission_id=sub_id,
                                workflow_run_id=session_id,
                                transcription=tr.transcription,
                                transcription_confidence=tr.confidence,
                                transcribed_at=datetime.now(),
                            )
                            to_update.append(db_submission)
                            transcription_results.append((original, tr))

                        if to_update:
                            await _update_submissions(
                                db,
                                session,
                                to_update,
                                status=SubmissionStatus.transcribed,
                            )
                else:
                    await session.logger.info(
                        "Transcribing submissions individually..."
                    )
                    semaphore = asyncio.Semaphore(parallelism)

                    async def transcribe_one_and_persist(
                        submission: SDKSubmission,
                        semaphore: asyncio.Semaphore,
                    ) -> Tuple[SDKSubmission, TranscribedSubmission] | None:
                        async with semaphore:
                            try:
                                if inspect.iscoroutinefunction(
                                    transcriber_instance.transcribe
                                ):
                                    result = await transcriber_instance.transcribe(
                                        submission
                                    )
                                else:
                                    loop = asyncio.get_running_loop()
                                    result = await loop.run_in_executor(
                                        None,
                                        transcriber_instance.transcribe,
                                        submission,
                                    )

                                sub_id = UUID(submission.id)
                                with get_session() as db:
                                    db_submission = db.get(Submission, sub_id)
                                    if not db_submission:
                                        await session.logger.warning(
                                            f"Can't find {submission.submitter.name}'s submission"
                                        )
                                        return None

                                    await _upsert_submission_result(
                                        db,
                                        session,
                                        sub_id,
                                        session_id,
                                        transcription=result.transcription,
                                        transcription_confidence=result.confidence,
                                        transcribed_at=datetime.now(),
                                    )

                                    db_submission.status = SubmissionStatus.transcribed
                                    db.commit()
                                    await session.bus.emit(
                                        "update",
                                        {
                                            # TODO: frontend expects "submissions", in plural, to invalidate that query. Should we change that?
                                            "object": "submissions",
                                            "type": "update",
                                            "payload": {
                                                "id": db_submission.id,
                                                "status": db_submission.status,
                                            },
                                        },
                                    )

                                return (submission, result)
                            except Exception as e:
                                sub_id = UUID(submission.id)
                                with get_session() as db:
                                    db_sub = db.get(Submission, sub_id)
                                    if db_sub:
                                        await session.logger.error(
                                            f"Transcription failed for {submission.submitter.name}'s submission: {e}"
                                        )
                                        db_sub.status = SubmissionStatus.failure
                                        db.commit()
                                        await session.bus.emit(
                                            "update",
                                            {
                                                "object": "submissions",
                                                "type": "update",
                                                "payload": {
                                                    "id": db_sub.id,
                                                    "status": db_sub.status,
                                                },
                                            },
                                        )
                                return None

                    results = await asyncio.gather(
                        *[
                            transcribe_one_and_persist(sub, semaphore)
                            for sub in sdk_submissions
                        ]
                    )
                    transcription_results = [r for r in results if r is not None]

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
                # Filter out successful transcriptions (already shaped accordingly)
                valid_t_results: List[Tuple[SDKSubmission, TranscribedSubmission]] = [
                    (o, t) for (o, t) in transcription_results
                ]

                db_subs = []
                with get_session() as db:
                    for original, _ in valid_t_results:
                        db_sub = db.get(Submission, UUID(original.id))
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
                    grading_results: List[
                        Tuple[SDKSubmission, TranscribedSubmission, GradeResult]
                    ] = []
                else:
                    use_batch_grade = is_method_overridden(
                        grader_instance, "grade_batch", GradePlugin
                    )

                    grading_results: List[
                        Tuple[SDKSubmission, TranscribedSubmission, GradeResult]
                    ] = []

                    if use_batch_grade:
                        await session.logger.info(
                            "Using batch grading (plugin override detected)"
                        )
                        pairs = [(t, o) for (o, t) in valid_t_results]
                        if inspect.iscoroutinefunction(grader_instance.grade_batch):
                            batch = await grader_instance.grade_batch(pairs)
                        else:
                            loop = asyncio.get_running_loop()
                            batch = await loop.run_in_executor(
                                None, grader_instance.grade_batch, pairs
                            )
                        if not isinstance(batch, list) or len(batch) != len(
                            valid_t_results
                        ):
                            raise RuntimeError(
                                "Batch grading returned unexpected result length"
                            )
                        with get_session() as db:
                            to_update_success: List[Submission] = []
                            for idx, grade_result in enumerate(batch):
                                original, transcribed = valid_t_results[idx]
                                original_id = UUID(original.id)
                                db_sub = db.get(Submission, original_id)
                                if not db_sub:
                                    await session.logger.warning(
                                        f"Can't find {original.submitter.name}'s submission, skipping."
                                    )
                                    continue
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
                                grading_results.append(
                                    (original, transcribed, grade_result)
                                )
                            if to_update_success:
                                await _update_submissions(
                                    db,
                                    session,
                                    to_update_success,
                                    status=SubmissionStatus.graded,
                                )
                    else:
                        await session.logger.info(
                            "Using individual grading with streaming"
                        )
                        semaphore = asyncio.Semaphore(parallelism)

                        async def grade_one_and_persist(
                            original: SDKSubmission,
                            transcribed_result: TranscribedSubmission,
                            semaphore: asyncio.Semaphore,
                        ) -> Tuple[SDKSubmission, TranscribedSubmission, GradeResult] | None:
                            async with semaphore:
                                try:
                                    if inspect.iscoroutinefunction(
                                        grader_instance.grade
                                    ):
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

                                    original_id = UUID(original.id)
                                    with get_session() as db:
                                        db_sub = db.get(Submission, original_id)
                                        if not db_sub:
                                            await session.logger.warning(
                                                f"Can't find {original.submitter.name}'s submission, skipping."
                                            )
                                            return None

                                        await _upsert_submission_result(
                                            db,
                                            session,
                                            submission_id=original_id,
                                            workflow_run_id=session_id,
                                            score=result.score,
                                            feedback=result.feedback,
                                            grading_meta=result.meta,
                                            graded_at=datetime.now(),
                                        )

                                        db_sub.status = SubmissionStatus.graded
                                        db.commit()
                                        await session.bus.emit(
                                            "update",
                                            {
                                                "object": "submissions",
                                                "type": "update",
                                                "payload": {
                                                    "id": db_sub.id,
                                                    "status": db_sub.status,
                                                },
                                            },
                                        )

                                    return (
                                        original,
                                        transcribed_result,
                                        result,
                                    )
                                except Exception as e:
                                    original_id = UUID(original.id)
                                    with get_session() as db:
                                        db_sub = db.get(Submission, original_id)
                                        if db_sub:
                                            await session.logger.error(
                                                f"Grading failed for {original.submitter.name}'s submission: {e}"
                                            )
                                            db_sub.status = SubmissionStatus.failure
                                            db.commit()
                                            await session.bus.emit(
                                                "update",
                                                {
                                                    "object": "submissions",
                                                    "type": "update",
                                                    "payload": {
                                                        "id": db_sub.id,
                                                        "status": db_sub.status,
                                                    },
                                                },
                                            )
                                    return None

                        graded_streamed = await asyncio.gather(
                            *[
                                grade_one_and_persist(o, t, semaphore)
                                for (o, t) in valid_t_results
                            ]
                        )
                        grading_results = [
                            r for r in graded_streamed if r is not None
                        ]

            except Exception as e:
                return await report_failure(
                    session,
                    session_id,
                    submission_ids,
                    reason="Session failed due to grading error",
                    log_message=f"Grading failed: {e}",
                )

            await session.logger.info("Grading step completed")

        # Validation step
        if getattr(workflow, "validator_plugin_id", None):
            await session.logger.info("Starting validation step")
            validator_cls = get_plugin_object(workflow.validator_plugin_id)
            if not validator_cls:
                await session.logger.warning("Validator plugin not found, skipping")
            else:
                try:
                    validator_instance = validator_cls(
                        session.logger.get_child(workflow.validator_plugin_id)
                    )
                    validator_instance.set_values(workflow.validator_settings or {})

                    # Build inputs from grading_results (if any)
                    # grading_results should be defined from previous block
                    if 'grading_results' not in locals():
                        grading_results = []  # type: ignore

                    use_batch_validate = is_method_overridden(
                        validator_instance, "validate_batch", ValidationPlugin
                    )

                    async def apply_validation_to_db(
                        sub_id: UUID, validation: ValidationResult
                    ) -> None:
                        with get_session() as db:
                            db_sub = db.get(Submission, sub_id)
                            if not db_sub:
                                return
                            result = (
                                db.query(SubmissionResult)
                                .filter(
                                    SubmissionResult.submission_id == sub_id,
                                    SubmissionResult.workflow_run_id == session_id,
                                )
                                .first()
                            )
                            if result:
                                if validation.modified_score is not None:
                                    result.score = validation.modified_score
                                if validation.modified_feedback is not None:
                                    result.feedback = validation.modified_feedback
                                meta = result.grading_meta or {}
                                meta["validation"] = {
                                    "is_valid": validation.is_valid,
                                    "notes": validation.validation_notes,
                                    "meta": validation.meta,
                                }
                                result.grading_meta = meta
                                result.graded_at = result.graded_at or datetime.now()
                                db.commit()
                                await session.bus.emit(
                                    "update",
                                    {
                                        "object": "submissions",
                                        "type": "update",
                                        "payload": {"id": db_sub.id},
                                    },
                                )

                    if not grading_results:
                        await session.logger.info(
                            "No graded submissions to validate, skipping"
                        )
                    elif use_batch_validate:
                        await session.logger.info(
                            "Using batch validation..."
                        )
                        items = [(o, t, g) for (o, t, g) in grading_results]
                        if inspect.iscoroutinefunction(
                            validator_instance.validate_batch
                        ):
                            v_results = await validator_instance.validate_batch(items)
                        else:
                            loop = asyncio.get_running_loop()
                            v_results = await loop.run_in_executor(
                                None, validator_instance.validate_batch, items
                            )
                        # Emit a single batch update after persisting
                        batched_payload = []
                        for idx, v in enumerate(v_results):
                            original, _, _ = grading_results[idx]
                            sub_id = UUID(original.id)
                            await apply_validation_to_db(sub_id, v)
                            batched_payload.append({"id": sub_id})
                        if batched_payload:
                            await session.bus.emit(
                                "update",
                                {
                                    "object": "submissions",
                                    "type": "update",
                                    "payload": batched_payload,
                                },
                            )
                    else:
                        await session.logger.info(
                            "Using individual validation with streaming"
                        )
                        semaphore = asyncio.Semaphore(parallelism)

                        async def validate_one_and_persist(
                            original: SDKSubmission,
                            transcribed: TranscribedSubmission,
                            graded: GradeResult,
                            semaphore: asyncio.Semaphore,
                        ) -> None:
                            async with semaphore:
                                try:
                                    if inspect.iscoroutinefunction(
                                        validator_instance.validate_one
                                    ):
                                        v = await validator_instance.validate_one(
                                            original, transcribed, graded
                                        )
                                    else:
                                        loop = asyncio.get_running_loop()
                                        v = await loop.run_in_executor(
                                            None,
                                            validator_instance.validate_one,
                                            original,
                                            transcribed,
                                            graded,
                                        )
                                    await apply_validation_to_db(UUID(original.id), v)
                                except Exception as e:
                                    await session.logger.error(
                                        f"Validation failed for {original.submitter.name}'s submission: {e}"
                                    )

                        await asyncio.gather(
                            *[
                                validate_one_and_persist(o, t, g, semaphore)
                                for (o, t, g) in grading_results
                            ]
                        )
                except Exception as e:
                    await session.logger.error(
                        f"Validation step failed: {e} — continuing to finalize run"
                    )

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
