from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from fair_platform.backend.api.schema.utils import to_camel_case


class SubmitterBase(BaseModel):
    name: str
    email: Optional[str] = None
    user_id: Optional[UUID] = None
    is_synthetic: bool = False

    class Config:
        from_attributes = True
        alias_generator = to_camel_case
        populate_by_name = True


class SubmitterCreate(SubmitterBase):
    pass


class SubmitterRead(SubmitterBase):
    id: UUID
    created_at: datetime


__all__ = ["SubmitterBase", "SubmitterCreate", "SubmitterRead"]
