from typing import Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from fair_platform.backend.api.schema.plugin import ExtensionPlugin
from fair_platform.backend.api.schema.workflow_run import WorkflowRunBase
from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.extension_sdk.contracts.plugin import PluginType


class WorkflowStep(BaseModel):
    model_config = schema_config

    id: str
    order: int = Field(ge=0)
    plugin_type: PluginType
    plugin: ExtensionPlugin
    settings: dict = Field(default_factory=dict)


class WorkflowBase(BaseModel):
    model_config = schema_config

    name: str
    course_id: UUID
    description: Optional[str] = None
    steps: list[WorkflowStep] = Field(default_factory=list)


class WorkflowCreate(WorkflowBase):
    pass


class WorkflowUpdate(BaseModel):
    model_config = schema_config

    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[list[WorkflowStep]] = None


class WorkflowRead(WorkflowBase):
    id: UUID
    created_at: datetime
    created_by: UUID
    updated_at: Optional[datetime] = None
    archived: bool = False
    runs: Optional[list[WorkflowRunBase]] = None


__all__ = [
    "WorkflowBase",
    "WorkflowCreate",
    "WorkflowRead",
    "WorkflowStep",
    "WorkflowUpdate",
]
