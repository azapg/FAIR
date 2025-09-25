from typing import Optional, Dict, List, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from fair_platform.backend.api.schema.workflow_run import WorkflowRunBase


class PluginConfig(BaseModel):
    """Configuration for a single plugin in a workflow."""
    plugin_id: str
    plugin_hash: Optional[str] = None  # For reproducibility
    settings: Dict[str, Any] = {}


class WorkflowBase(BaseModel):
    name: str
    course_id: UUID
    description: Optional[str] = None
    plugin_configs: Optional[Dict[str, PluginConfig]] = {}  # plugin_type -> PluginConfig

    class Config:
        from_attributes = True


class WorkflowCreate(WorkflowBase):
    created_by: UUID


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    plugin_configs: Optional[Dict[str, PluginConfig]] = None

    class Config:
        from_attributes = True


class WorkflowRead(WorkflowBase):
    id: UUID
    created_at: datetime
    created_by: UUID
    updated_at: Optional[datetime] = None
    runs: Optional[List[WorkflowRunBase]] = None


__all__ = [
    "PluginConfig", 
    "WorkflowBase",
    "WorkflowCreate",
    "WorkflowUpdate",
    "WorkflowRead",
]
