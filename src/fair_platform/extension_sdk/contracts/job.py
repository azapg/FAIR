from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator

from fair_platform.extension_sdk.contracts.common import contract_model_config
from fair_platform.extension_sdk.contracts.rubric import RubricJobRequest


class ActionPayload(BaseModel):
    model_config = contract_model_config

    action: str = Field(min_length=1)
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_params(self) -> "ActionPayload":
        if self.action == "rubric.create":
            self.params = RubricJobRequest.model_validate(self.params).model_dump()
        return self


class ProgressPayload(BaseModel):
    model_config = contract_model_config

    percent: int = Field(ge=0, le=100)
    message: str | None = None


class LogPayload(BaseModel):
    model_config = contract_model_config

    level: Literal["debug", "info", "warn", "error"]
    output: str


class TokenPayload(BaseModel):
    model_config = contract_model_config

    text: str


class ResultPayload(BaseModel):
    model_config = contract_model_config

    data: dict[str, Any]


class ErrorPayload(BaseModel):
    model_config = contract_model_config

    error: str
    traceback: str | None = None


class JobUpdateProgress(BaseModel):
    model_config = contract_model_config

    event: Literal["progress"]
    payload: ProgressPayload


class JobUpdateLog(BaseModel):
    model_config = contract_model_config

    event: Literal["log"]
    payload: LogPayload


class JobUpdateToken(BaseModel):
    model_config = contract_model_config

    event: Literal["token"]
    payload: TokenPayload


class JobUpdateResult(BaseModel):
    model_config = contract_model_config

    event: Literal["result"]
    payload: ResultPayload


class JobUpdateError(BaseModel):
    model_config = contract_model_config

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
    model_config = contract_model_config

    update: JobUpdateEvent
    status: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


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
    "JobUpdateRequest",
]
