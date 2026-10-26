from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from fair_platform.extension_sdk.contracts.common import contract_model_config


EventVisibility = Literal["user", "operator", "private"]
EventDurability = Literal["durable"]


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionEventCreate(BaseModel):
    """Producer-to-FAIR event payload.

    The producer identity is intentionally separate from FAIR's server ID and
    sequence. Retries resend the same producer_event_id; FAIR assigns ordering.
    """

    model_config = contract_model_config

    producer_source: str = Field(min_length=1, max_length=255)
    producer_event_id: str = Field(min_length=1, max_length=255)
    producer_sequence: int | None = Field(default=None, ge=1)
    type: str = Field(min_length=1, max_length=255)
    schema_uri: str = Field(min_length=1, max_length=2048)
    occurred_at: datetime = Field(default_factory=_utc_now)
    visibility: EventVisibility = "user"
    durability: EventDurability = "durable"
    payload: dict[str, Any] = Field(default_factory=dict)
    parent_event_id: UUID | None = None
    trace_id: str | None = Field(default=None, max_length=128)
    span_id: str | None = Field(default=None, max_length=128)

    @field_validator("schema_uri")
    @classmethod
    def schema_uri_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("schema_uri must not be blank")
        return value


class ExecutionEventRead(ExecutionEventCreate):
    """Server-accepted event envelope returned by FAIR."""

    id: UUID
    execution_id: UUID
    sequence: int = Field(ge=1)
    received_at: datetime


class ExecutionEventBatch(BaseModel):
    model_config = contract_model_config

    contract: Literal["fair.execution-event.v1"] = "fair.execution-event.v1"
    events: list[ExecutionEventCreate] = Field(min_length=1, max_length=100)


__all__ = [
    "EventDurability",
    "EventVisibility",
    "ExecutionEventBatch",
    "ExecutionEventCreate",
    "ExecutionEventRead",
]
