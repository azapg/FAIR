from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.api.schema.submission import SubmissionBase
from fair_platform.backend.data.models.workflow_run import WorkflowRunStatus
from fair_platform.backend.api.schema.utils import to_camel_case


class WorkflowRunBase(BaseModel):
    status: WorkflowRunStatus
    logs: Optional[Dict[str, Any]] = None
    submissions: Optional[List[SubmissionBase]] = None

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRunUpdate(BaseModel):
    status: Optional[WorkflowRunStatus] = None
    finished_at: Optional[datetime] = None
    logs: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class WorkflowRunRead(WorkflowRunBase):
    id: UUID
    run_by: UUID
    started_at: Optional[datetime]
    finished_at: Optional[datetime] = None


__all__ = [
    "WorkflowRunStatus",
    "WorkflowRunBase",
    "WorkflowRunCreate",
    "WorkflowRunUpdate",
    "WorkflowRunRead",
]
