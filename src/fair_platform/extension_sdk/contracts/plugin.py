from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from fair_platform.extension_sdk.contracts.common import contract_model_config


PluginType = Literal["transcriber", "grader", "reviewer"]


class PluginDescriptor(BaseModel):
    model_config = contract_model_config

    plugin_id: str = Field(min_length=1)
    extension_id: str = Field(min_length=1)
    plugin_type: PluginType
    name: str = Field(min_length=1)
    description: str | None = None
    version: str | None = None
    action: str = Field(min_length=1)
    settings_schema: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SubmissionArtifactRef(BaseModel):
    model_config = contract_model_config

    artifact_id: str
    title: str | None = None
    mime: str | None = None
    kind: str | None = None


class SubmissionPipelineState(BaseModel):
    model_config = contract_model_config

    transcription: str | None = None
    transcription_metadata: dict[str, Any] = Field(default_factory=dict)
    grade: float | None = None
    feedback: str | None = None
    grading_metadata: dict[str, Any] = Field(default_factory=dict)
    review_comments: list[str] = Field(default_factory=list)
    review_flags: list[str] = Field(default_factory=list)
    review_metadata: dict[str, Any] = Field(default_factory=dict)


class SubmissionExecutionInput(BaseModel):
    model_config = contract_model_config

    submission_id: str
    assignment_id: str | None = None
    status: str | None = None
    artifacts: list[SubmissionArtifactRef] = Field(default_factory=list)
    state: SubmissionPipelineState = Field(default_factory=SubmissionPipelineState)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepExecutionRequest(BaseModel):
    model_config = contract_model_config

    workflow_run_id: str
    step_id: str
    step_index: int = Field(ge=0)
    plugin: PluginDescriptor
    settings: dict[str, Any] = Field(default_factory=dict)
    submissions: list[SubmissionExecutionInput] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TranscriberSubmissionResult(BaseModel):
    model_config = contract_model_config

    submission_id: str
    transcription: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraderSubmissionResult(BaseModel):
    model_config = contract_model_config

    submission_id: str
    grade: float | None = None
    feedback: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReviewerSubmissionResult(BaseModel):
    model_config = contract_model_config

    submission_id: str
    comments: list[str] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowStepExecutionResult(BaseModel):
    model_config = contract_model_config

    plugin_type: PluginType
    results: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


__all__ = [
    "PluginType",
    "PluginDescriptor",
    "SubmissionArtifactRef",
    "SubmissionPipelineState",
    "SubmissionExecutionInput",
    "WorkflowStepExecutionRequest",
    "TranscriberSubmissionResult",
    "GraderSubmissionResult",
    "ReviewerSubmissionResult",
    "WorkflowStepExecutionResult",
]
