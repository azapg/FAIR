from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from fair_platform.backend.api.schema.utils import schema_config


class SubmitterBase(BaseModel):
    model_config = schema_config
    
    name: str
    email: Optional[str] = None
    user_id: Optional[UUID] = None
    is_synthetic: bool = False


class SubmitterCreate(SubmitterBase):
    pass


class SubmitterRead(SubmitterBase):
    id: UUID
    created_at: datetime


__all__ = ["SubmitterBase", "SubmitterCreate", "SubmitterRead"]
