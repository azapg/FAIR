from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from fair_platform.backend.data.models.submission import Submission, SubmissionStatus
from fair_platform.backend.data.models.submission_event import (
    SubmissionEvent,
    SubmissionEventType,
)
from fair_platform.backend.data.models.user import User


class SubmissionManager:

    def __init__(self, db: Session):
        self.db = db

    def _log_event(
        self,
        submission_id: UUID,
        event_type: SubmissionEventType,
        actor_id: Optional[UUID] = None,
        workflow_run_id: Optional[UUID] = None,
        details: Optional[dict] = None,
    ) -> SubmissionEvent:
        event = SubmissionEvent(
            id=uuid4(),
            submission_id=submission_id,
            event_type=event_type,
            actor_id=actor_id,
            workflow_run_id=workflow_run_id,
            details=details,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def record_ai_result(
        self,
        submission_id: UUID,
        score: float,
        feedback: str,
        workflow_run_id: UUID,
    ) -> Submission:
        sub = self.db.get(Submission, submission_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found",
            )

        sub.draft_score = score
        sub.draft_feedback = feedback

        self._log_event(
            submission_id=sub.id,
            event_type=SubmissionEventType.ai_graded,
            workflow_run_id=workflow_run_id,
            details={"score": score, "feedback": feedback},
        )
        return sub

    def update_draft(
        self,
        submission_id: UUID,
        score: Optional[float],
        feedback: Optional[str],
        actor: User,
    ) -> Submission:
        sub = self.db.get(Submission, submission_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found",
            )

        if sub.status == SubmissionStatus.pending:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot edit draft before submission has been processed",
            )

        changes: dict = {}
        if score is not None and score != sub.draft_score:
            changes["score"] = {"old": sub.draft_score, "new": score}
            sub.draft_score = score
        if feedback is not None and feedback != sub.draft_feedback:
            changes["feedback"] = {"old": sub.draft_feedback, "new": feedback}
            sub.draft_feedback = feedback

        if not changes:
            return sub

        self._log_event(
            submission_id=sub.id,
            event_type=SubmissionEventType.manual_edit,
            actor_id=actor.id,
            details=changes,
        )
        return sub

    def return_to_student(
        self,
        submission_id: UUID,
        actor: User,
    ) -> Submission:
        sub = self.db.get(Submission, submission_id)
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Submission not found",
            )

        if sub.draft_score is None and sub.draft_feedback is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No draft data to publish",
            )

        sub.published_score = sub.draft_score
        sub.published_feedback = sub.draft_feedback
        sub.returned_at = datetime.utcnow()
        sub.status = SubmissionStatus.returned

        self._log_event(
            submission_id=sub.id,
            event_type=SubmissionEventType.returned,
            actor_id=actor.id,
            details={
                "published_score": sub.published_score,
                "published_feedback": sub.published_feedback,
            },
        )
        return sub


def get_submission_manager(db: Session) -> SubmissionManager:
    return SubmissionManager(db)


__all__ = ["SubmissionManager", "get_submission_manager"]
