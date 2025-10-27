from typing import Optional, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.data.models.submission import SubmissionStatus
from fair_platform.backend.api.schema.user import UserRead
from fair_platform.backend.api.schema.artifact import ArtifactRead
from fair_platform.backend.api.schema.submission_result import SubmissionResultRead


class SubmissionBase(BaseModel):
    assignment_id: UUID
    submitter_id: UUID
    submitted_at: Optional[datetime] = None
    status: SubmissionStatus = SubmissionStatus.pending
    official_run_id: Optional[UUID] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        validate_by_name = True


class SubmissionCreate(SubmissionBase):
    artifact_ids: Optional[List[UUID]] = None
    run_ids: Optional[List[UUID]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        validate_by_name = True


class SubmissionUpdate(BaseModel):
    submitted_at: Optional[datetime] = None
    status: Optional[SubmissionStatus] = None
    official_run_id: Optional[UUID] = None
    artifact_ids: Optional[List[UUID]] = None  # full replace if provided
    run_ids: Optional[List[UUID]] = None  # full replace if provided

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: "".join(
            word.capitalize() if i > 0 else word
            for i, word in enumerate(field_name.split("_"))
        )
        validate_by_name = True


class SubmissionRead(SubmissionBase):
    id: UUID
    submitter: Optional[UserRead] = None
    artifacts: List[ArtifactRead] = []
    official_result: Optional[SubmissionResultRead] = None


__all__ = [
    "SubmissionStatus",
    "SubmissionBase",
    "SubmissionCreate",
    "SubmissionUpdate",
    "SubmissionRead",
]
