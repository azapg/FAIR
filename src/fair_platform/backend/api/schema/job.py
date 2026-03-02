from typing import Any

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.rubric import RubricGenerateResponse
from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.services.job_queue import JobStatus
from fair_platform.extension_sdk.contracts.job import (
    ActionPayload,
    ErrorPayload,
    JobUpdateError,
    JobUpdateEvent,
    JobUpdateLog,
    JobUpdateProgress,
    JobUpdateResult,
    JobUpdateToken,
    LogPayload,
    ProgressPayload,
    ResultPayload,
    TokenPayload,
)


class JobCreateRequest(BaseModel):
    model_config = schema_config

    target: str = Field(min_length=1)
    payload: "ActionPayload"
    metadata: dict[str, Any] = Field(default_factory=dict)
    job_id: str | None = None


class JobCreateResponse(BaseModel):
    model_config = schema_config

    job_id: str
    status: JobStatus


class JobStateRead(BaseModel):
    model_config = schema_config

    job_id: str
    status: JobStatus
    updated_at: str
    details: dict[str, Any] = Field(default_factory=dict)


class RubricResultPayload(BaseModel):
    model_config = schema_config

    data: RubricGenerateResponse


class JobUpdateRequest(BaseModel):
    model_config = schema_config

    update: JobUpdateEvent
    status: JobStatus | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class JobUpdateResponse(BaseModel):
    model_config = schema_config

    job_id: str
    accepted: bool
    status: JobStatus | None = None


__all__ = [
    "ActionPayload",
    "ProgressPayload",
    "LogPayload",
    "TokenPayload",
    "ResultPayload",
    "RubricResultPayload",
    "ErrorPayload",
    "JobUpdateProgress",
    "JobUpdateLog",
    "JobUpdateToken",
    "JobUpdateResult",
    "JobUpdateError",
    "JobUpdateEvent",
    "JobCreateRequest",
    "JobCreateResponse",
    "JobStateRead",
    "JobUpdateRequest",
    "JobUpdateResponse",
]
