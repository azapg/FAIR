from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.extension_sdk.contracts.rubric import (
    RubricContent,
    RubricCriterion,
)


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


__all__ = [
    "RubricCriterion",
    "RubricContent",
    "RubricCreate",
    "RubricUpdate",
    "RubricRead",
]
