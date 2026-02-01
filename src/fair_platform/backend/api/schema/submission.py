from typing import Optional, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.data.models.submission import SubmissionStatus
from fair_platform.backend.api.schema.submitter import SubmitterRead
from fair_platform.backend.api.schema.artifact import ArtifactRead
from fair_platform.backend.api.schema.submission_result import SubmissionResultRead
from fair_platform.backend.api.schema.utils import schema_config


class SubmissionBase(BaseModel):
    model_config = schema_config
    
    assignment_id: UUID
    submitter_id: UUID
    created_by_id: UUID
    submitted_at: Optional[datetime] = None
    status: SubmissionStatus = SubmissionStatus.pending
    official_run_id: Optional[UUID] = None


class SubmissionCreate(SubmissionBase):
    model_config = schema_config
    
    artifact_ids: Optional[List[UUID]] = None
    run_ids: Optional[List[UUID]] = None


class SubmissionUpdate(BaseModel):
    model_config = schema_config
    
    official_run_id: Optional[UUID] = None
    artifact_ids: Optional[List[UUID]] = None  # full replace if provided


class SubmissionDraftUpdate(BaseModel):
    model_config = schema_config

    score: Optional[float] = None
    feedback: Optional[str] = None


class SubmissionRead(SubmissionBase):
    id: UUID
    submitter: Optional[SubmitterRead] = None
    artifacts: List[ArtifactRead] = []
    official_result: Optional[SubmissionResultRead] = None
    draft_score: Optional[float] = None
    draft_feedback: Optional[str] = None
    published_score: Optional[float] = None
    published_feedback: Optional[str] = None
    returned_at: Optional[datetime] = None


__all__ = [
    "SubmissionStatus",
    "SubmissionBase",
    "SubmissionCreate",
    "SubmissionUpdate",
    "SubmissionDraftUpdate",
    "SubmissionRead",
]
