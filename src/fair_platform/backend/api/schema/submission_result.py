from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel
from fair_platform.backend.api.schema.utils import schema_config


class SubmissionResultBase(BaseModel):
    model_config = schema_config
    
    transcription: Optional[str] = None
    transcription_confidence: Optional[float] = None
    transcribed_at: Optional[datetime] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    grading_meta: Optional[dict] = None
    graded_at: Optional[datetime] = None


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
