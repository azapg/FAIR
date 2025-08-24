from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from data.models.workflow_run import WorkflowRunStatus


class WorkflowRunBase(BaseModel):
    workflow_id: UUID
    run_by: UUID
    status: WorkflowRunStatus
    logs: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True
        orm_mode = True


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRunUpdate(BaseModel):
    status: Optional[WorkflowRunStatus] = None
    finished_at: Optional[datetime] = None
    logs: Optional[Dict[str, Any]] = None

    class Config:
        use_enum_values = True
        orm_mode = True


class WorkflowRunRead(WorkflowRunBase):
    id: UUID
    started_at: datetime
    finished_at: Optional[datetime] = None


__all__ = [
    "WorkflowRunStatus",
    "WorkflowRunBase",
    "WorkflowRunCreate",
    "WorkflowRunUpdate",
    "WorkflowRunRead",
]

