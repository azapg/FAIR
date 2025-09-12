from typing import Optional, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.data.models.submission import SubmissionStatus


class SubmissionBase(BaseModel):
    assignment_id: UUID
    submitter_id: UUID
    submitted_at: Optional[datetime] = None
    status: SubmissionStatus = SubmissionStatus.pending
    official_run_id: Optional[UUID] = None

    class Config:
        use_enum_values = True
        orm_mode = True


class SubmissionCreate(SubmissionBase):
    artifact_ids: Optional[List[UUID]] = None
    run_ids: Optional[List[UUID]] = None


class SubmissionUpdate(BaseModel):
    submitted_at: Optional[datetime] = None
    status: Optional[SubmissionStatus] = None
    official_run_id: Optional[UUID] = None
    artifact_ids: Optional[List[UUID]] = None  # full replace if provided
    run_ids: Optional[List[UUID]] = None      # full replace if provided

    class Config:
        use_enum_values = True
        orm_mode = True


class SubmissionRead(SubmissionBase):
    id: UUID


__all__ = [
    "SubmissionStatus",
    "SubmissionBase",
    "SubmissionCreate",
    "SubmissionUpdate",
    "SubmissionRead",
]

