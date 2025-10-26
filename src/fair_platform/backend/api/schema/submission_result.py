from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubmissionResultBase(BaseModel):
    transcription: Optional[str] = None
    transcription_confidence: Optional[float] = None
    transcribed_at: Optional[datetime] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    grading_meta: Optional[dict] = None
    graded_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        validate_by_name = True


class SubmissionResultRead(SubmissionResultBase):
    id: UUID
    submission_id: UUID
    workflow_run_id: UUID


class SubmissionResultCreate(SubmissionResultBase):
    submission_id: UUID
    workflow_run_id: UUID


class SubmissionResultUpdate(SubmissionResultBase):
    pass


__all__ = [
    "SubmissionResultBase",
    "SubmissionResultRead",
    "SubmissionResultCreate",
    "SubmissionResultUpdate",
]
