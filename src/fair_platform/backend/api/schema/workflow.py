from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel

from fair_platform.backend.api.schema.plugin import RuntimePlugin
from fair_platform.backend.api.schema.workflow_run import WorkflowRunBase
from fair_platform.backend.api.schema.utils import schema_config


class WorkflowBase(BaseModel):
    model_config = schema_config
    
    name: str
    course_id: UUID
    description: Optional[str] = None
    plugins: Optional[Dict[str, RuntimePlugin]] = None


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    model_config = schema_config
    
    name: Optional[str] = None
    description: Optional[str] = None
    plugins: Optional[Dict[str, RuntimePlugin]] = None


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
