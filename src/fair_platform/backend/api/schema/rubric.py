from uuid import UUID
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from fair_platform.backend.api.schema.utils import schema_config


class RubricCreate(BaseModel):
    model_config = schema_config

    name: str
    content: dict


class RubricRead(BaseModel):
    model_config = schema_config

    id: UUID
    name: str
    created_by_id: UUID
    content: dict
    created_at: datetime


__all__ = ["RubricCreate", "RubricRead"]
