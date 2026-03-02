from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.services.job_queue import JobStatus


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


class ActionPayload(BaseModel):
    model_config = schema_config

    action: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)


class ProgressPayload(BaseModel):
    model_config = schema_config

    percent: int = Field(ge=0, le=100)
    message: str | None = None


class LogPayload(BaseModel):
    model_config = schema_config

    level: Literal["debug", "info", "warn", "error"]
    output: str


class TokenPayload(BaseModel):
    model_config = schema_config

    text: str


class ResultPayload(BaseModel):
    model_config = schema_config

    data: dict[str, Any]


class ErrorPayload(BaseModel):
    model_config = schema_config

    error: str
    traceback: str | None = None


class JobUpdateProgress(BaseModel):
    model_config = schema_config

    event: Literal["progress"]
    payload: ProgressPayload


class JobUpdateLog(BaseModel):
    model_config = schema_config

    event: Literal["log"]
    payload: LogPayload


class JobUpdateToken(BaseModel):
    model_config = schema_config

    event: Literal["token"]
    payload: TokenPayload


class JobUpdateResult(BaseModel):
    model_config = schema_config

    event: Literal["result"]
    payload: ResultPayload


class JobUpdateError(BaseModel):
    model_config = schema_config

    event: Literal["error"]
    payload: ErrorPayload


JobUpdateEvent = Annotated[
    JobUpdateProgress
    | JobUpdateLog
    | JobUpdateToken
    | JobUpdateResult
    | JobUpdateError,
    Field(discriminator="event"),
]


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
