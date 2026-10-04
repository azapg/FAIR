from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from fair_platform.backend.data.models.submission_event import SubmissionEventType
from fair_platform.backend.data.models.execution import ExecutionKind, ExecutionStatus
from fair_platform.backend.api.schema.utils import schema_config


class TimelineActorRead(BaseModel):
    model_config = schema_config

    name: str


class TimelineExecutionRead(BaseModel):
    model_config = schema_config

    id: UUID
    status: ExecutionStatus
    kind: ExecutionKind
    capability_id: Optional[str] = None
    flow_version_id: Optional[UUID] = None


class SubmissionTimelineEventRead(BaseModel):
    model_config = schema_config

    id: UUID
    submission_id: UUID
    event_type: SubmissionEventType
    actor: Optional[TimelineActorRead] = None
    execution: Optional[TimelineExecutionRead] = None
    details: Optional[dict] = None
    created_at: datetime


__all__ = [
    "TimelineActorRead",
    "TimelineExecutionRead",
    "SubmissionTimelineEventRead",
]
