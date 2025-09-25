from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.api.schema.plugin import PluginBase
from fair_platform.backend.api.schema.workflow_run import WorkflowRunBase


class WorkflowBase(BaseModel):
    name: str
    course_id: UUID
    description: Optional[str] = None
    plugins: Optional[Dict[str, PluginBase]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: ''.join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
        validate_by_name = True


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    plugins: Optional[Dict[str, PluginBase]] = None

    class Config:
        from_attributes = True
        alias_generator = lambda field_name: ''.join(
            word.capitalize() if i > 0 else word for i, word in enumerate(field_name.split('_')))
        validate_by_name = True


class WorkflowRead(WorkflowBase):
    id: UUID
    created_at: datetime
    created_by: UUID
    updated_at: Optional[datetime] = None
    runs: Optional[List[WorkflowRunBase]] = None


__all__ = [
    "WorkflowBase",
    "WorkflowCreate",
    "WorkflowUpdate",
    "WorkflowRead",
]
