from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from fair_platform.backend.api.schema.utils import schema_config


class RubricCriterion(BaseModel):
    model_config = schema_config

    name: str
    weight: float
    levels: list[str]


class RubricContent(BaseModel):
    model_config = schema_config

    levels: list[str]
    criteria: list[RubricCriterion]


class RubricCreate(BaseModel):
    model_config = schema_config

    name: str
    content: RubricContent


class RubricUpdate(BaseModel):
    model_config = schema_config

    name: str | None = None
    content: RubricContent | None = None


class RubricRead(BaseModel):
    model_config = schema_config

    id: UUID
    name: str
    created_by_id: UUID
    content: RubricContent
    created_at: datetime


class RubricJobRequest(BaseModel):
    model_config = schema_config

    instruction: str = Field(min_length=1)

    @field_validator("instruction")
    @classmethod
    def validate_instruction(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Instruction cannot be empty")
        return normalized


class RubricGenerateRequest(RubricJobRequest):
    model_config = schema_config


class RubricGenerateResponse(BaseModel):
    model_config = schema_config

    content: RubricContent


__all__ = [
    "RubricCriterion",
    "RubricContent",
    "RubricJobRequest",
    "RubricCreate",
    "RubricUpdate",
    "RubricRead",
    "RubricGenerateRequest",
    "RubricGenerateResponse",
]
