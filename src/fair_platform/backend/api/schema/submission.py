from typing import Optional, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.data.models.submission import SubmissionStatus
from fair_platform.backend.api.schema.submitter import SubmitterRead
from fair_platform.backend.api.schema.artifact import ArtifactRead
from fair_platform.backend.api.schema.submission_result import SubmissionResultRead
from fair_platform.backend.api.schema.utils import to_camel_case


class SubmissionBase(BaseModel):
    assignment_id: UUID
    submitter_id: UUID
    created_by_id: UUID
    submitted_at: Optional[datetime] = None
    status: SubmissionStatus = SubmissionStatus.pending
    official_run_id: Optional[UUID] = None

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class SubmissionCreate(SubmissionBase):
    artifact_ids: Optional[List[UUID]] = None
    run_ids: Optional[List[UUID]] = None

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class SubmissionUpdate(BaseModel):
    official_run_id: Optional[UUID] = None
    artifact_ids: Optional[List[UUID]] = None  # full replace if provided

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class SubmissionRead(SubmissionBase):
    id: UUID
    submitter: Optional[SubmitterRead] = None
    artifacts: List[ArtifactRead] = []
    official_result: Optional[SubmissionResultRead] = None


__all__ = [
    "SubmissionStatus",
    "SubmissionBase",
    "SubmissionCreate",
    "SubmissionUpdate",
    "SubmissionRead",
]
