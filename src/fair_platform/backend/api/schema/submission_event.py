from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from fair_platform.backend.data.models.submission_event import SubmissionEventType
from fair_platform.backend.api.schema.utils import schema_config


class SubmissionEventRead(BaseModel):
    model_config = schema_config

    id: UUID
    submission_id: UUID
    event_type: SubmissionEventType
    actor_id: Optional[UUID] = None
    workflow_run_id: Optional[UUID] = None
    details: Optional[dict] = None
    created_at: datetime


__all__ = ["SubmissionEventRead"]
