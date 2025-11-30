from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.api.schema.submission import SubmissionBase
from fair_platform.backend.data.models.workflow_run import WorkflowRunStatus
from fair_platform.backend.api.schema.utils import schema_config


class WorkflowRunBase(BaseModel):
    model_config = schema_config
    
    status: WorkflowRunStatus
    logs: Optional[Dict[str, Any]] = None
    submissions: Optional[List[SubmissionBase]] = None


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRunUpdate(BaseModel):
    model_config = schema_config
    
    status: Optional[WorkflowRunStatus] = None
    finished_at: Optional[datetime] = None
    logs: Optional[Dict[str, Any]] = None


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
