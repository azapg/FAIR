from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.submission import SubmissionBase
from fair_platform.backend.data.models.workflow_run import WorkflowRunStatus
from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.api.schema.user import UserRead


class WorkflowRunStepState(BaseModel):
    model_config = schema_config

    step_id: str
    step_index: int = Field(ge=0)
    plugin_id: str
    plugin_type: str
    extension_id: str
    status: str
    job_id: str | None = None
    result: Dict[str, Any] | None = None
    error: str | None = None


class WorkflowRunBase(BaseModel):
    model_config = schema_config

    status: WorkflowRunStatus
    logs: Optional[Dict[str, Any]] = None
    submissions: Optional[List[SubmissionBase]] = None
    step_states: list[WorkflowRunStepState] = Field(default_factory=list)


class WorkflowRunCreateRequest(BaseModel):
    model_config = schema_config

    workflow_id: UUID
    submission_ids: list[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRunCreate(WorkflowRunBase):
    pass


class WorkflowRunUpdate(BaseModel):
    model_config = schema_config

    status: Optional[WorkflowRunStatus] = None
    finished_at: Optional[datetime] = None
    logs: Optional[Dict[str, Any]] = None


class WorkflowRunRead(WorkflowRunBase):
    id: UUID
    workflow_id: UUID
    runner: UserRead
    started_at: Optional[datetime]
    finished_at: Optional[datetime] = None
    request_payload: Dict[str, Any] | None = None


__all__ = [
    "WorkflowRunStatus",
    "WorkflowRunBase",
    "WorkflowRunCreate",
    "WorkflowRunCreateRequest",
    "WorkflowRunRead",
    "WorkflowRunStepState",
    "WorkflowRunUpdate",
]
