from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.api.schema.utils import schema_config


class RubricCreate(BaseModel):
    model_config = schema_config

    name: str
    content: dict


class RubricUpdate(BaseModel):
    model_config = schema_config

    name: str | None = None
    content: dict | None = None


class RubricRead(BaseModel):
    model_config = schema_config

    id: UUID
    name: str
    created_by_id: UUID
    content: dict
    created_at: datetime


class RubricGenerateRequest(BaseModel):
    model_config = schema_config

    instruction: str


class RubricGenerateResponse(BaseModel):
    model_config = schema_config

    content: dict


__all__ = [
    "RubricCreate",
    "RubricUpdate",
    "RubricRead",
    "RubricGenerateRequest",
    "RubricGenerateResponse",
]
