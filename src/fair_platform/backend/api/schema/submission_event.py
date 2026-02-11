from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from fair_platform.backend.data.models.submission_event import SubmissionEventType
from fair_platform.backend.data.models.workflow_run import WorkflowRunStatus
from fair_platform.backend.api.schema.utils import schema_config


class TimelineActorRead(BaseModel):
    model_config = schema_config

    name: str


class TimelineRunnerRead(BaseModel):
    model_config = schema_config

    name: str


class TimelineWorkflowRead(BaseModel):
    model_config = schema_config

    name: str


class TimelineWorkflowRunRead(BaseModel):
    model_config = schema_config

    id: UUID
    status: WorkflowRunStatus
    workflow: Optional[TimelineWorkflowRead] = None
    runner: Optional[TimelineRunnerRead] = None


class SubmissionTimelineEventRead(BaseModel):
    model_config = schema_config

    id: UUID
    submission_id: UUID
    event_type: SubmissionEventType
    actor: Optional[TimelineActorRead] = None
    workflow_run: Optional[TimelineWorkflowRunRead] = None
    details: Optional[dict] = None
    created_at: datetime


__all__ = [
    "TimelineActorRead",
    "TimelineRunnerRead",
    "TimelineWorkflowRead",
    "TimelineWorkflowRunRead",
    "SubmissionTimelineEventRead",
]
