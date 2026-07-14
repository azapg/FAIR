from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Column,
    Text,
    UUID as SAUUID,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from .types import json_document_type

if TYPE_CHECKING:
    from .assignment import Assignment
    from .course import Course
    from .submission import Submission


execution_submissions = Table(
    "execution_submissions",
    Base.metadata,
    Column(
        "execution_id",
        SAUUID,
        ForeignKey("executions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "submission_id",
        SAUUID,
        ForeignKey("submissions.id", ondelete="RESTRICT"),
        primary_key=True,
    ),
    Index(
        "ix_execution_submissions_submission",
        "submission_id",
        "execution_id",
    ),
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ThreadStatus(str, Enum):
    open = "open"
    archived = "archived"


class TurnStatus(str, Enum):
    open = "open"
    waiting = "waiting"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ExecutionKind(str, Enum):
    agent = "agent"
    action = "action"
    flow = "flow"
    flow_step = "flow_step"
    tool = "tool"
    system = "system"


class ExecutionStatus(str, Enum):
    queued = "queued"
    running = "running"
    waiting = "waiting"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"
    expired = "expired"


class EventVisibility(str, Enum):
    user = "user"
    operator = "operator"
    private = "private"


class EventDurability(str, Enum):
    durable = "durable"
    ephemeral = "ephemeral"


class InteractionStatus(str, Enum):
    pending = "pending"
    resolved = "resolved"
    declined = "declined"
    cancelled = "cancelled"
    expired = "expired"


class DispatchCommandKind(str, Enum):
    start = "start"
    resume = "resume"
    cancel = "cancel"


class DispatchStatus(str, Enum):
    pending = "pending"
    leased = "leased"
    dispatched = "dispatched"
    failed = "failed"
    dead_letter = "dead_letter"


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"
    system = "system"
    tool = "tool"


class MessageAuthorType(str, Enum):
    user = "user"
    extension = "extension"
    platform = "platform"
    system = "system"


class MessageStatus(str, Enum):
    streaming = "streaming"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class Thread(Base):
    __tablename__ = "threads"

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    owner_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    course_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )
    assignment_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("assignments.id", ondelete="RESTRICT"), nullable=True
    )
    submission_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("submissions.id", ondelete="RESTRICT"), nullable=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[ThreadStatus] = mapped_column(
        String(32), nullable=False, default=ThreadStatus.open
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    owner = relationship("User", foreign_keys=[owner_user_id])
    turns: Mapped[list["Turn"]] = relationship(
        "Turn", back_populates="thread", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="thread", cascade="all, delete-orphan"
    )
    executions: Mapped[list["Execution"]] = relationship(
        "Execution", back_populates="thread"
    )


class Turn(Base):
    __tablename__ = "turns"
    __table_args__ = (
        UniqueConstraint("thread_id", "ordinal", name="uq_turns_thread_ordinal"),
        UniqueConstraint(
            "thread_id", "client_request_id", name="uq_turns_thread_request"
        ),
        CheckConstraint("ordinal >= 1", name="ck_turns_ordinal_positive"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    client_request_id: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[TurnStatus] = mapped_column(
        String(32), nullable=False, default=TurnStatus.open
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    thread: Mapped[Thread] = relationship("Thread", back_populates="turns")
    creator = relationship("User", foreign_keys=[created_by_user_id])
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="turn", cascade="all, delete-orphan"
    )
    executions: Mapped[list["Execution"]] = relationship(
        "Execution", back_populates="turn"
    )


class Execution(Base):
    __tablename__ = "executions"
    __table_args__ = (
        CheckConstraint("attempt >= 1", name="ck_executions_attempt_positive"),
        CheckConstraint("id != parent_execution_id", name="ck_executions_no_self_parent"),
        CheckConstraint("id != retry_of_execution_id", name="ck_executions_no_self_retry"),
        UniqueConstraint(
            "root_execution_id",
            "flow_node_id",
            "attempt",
            name="uq_executions_flow_node_attempt",
        ),
        Index("ix_executions_thread_created", "thread_id", "created_at"),
        Index("ix_executions_root_created", "root_execution_id", "created_at"),
        Index("ix_executions_status_created", "status", "created_at"),
        Index("ix_executions_course_created", "course_id", "created_at"),
        Index("ix_executions_assignment_created", "assignment_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    thread_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("threads.id", ondelete="RESTRICT"), nullable=True
    )
    turn_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("turns.id", ondelete="RESTRICT"), nullable=True
    )
    course_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )
    assignment_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("assignments.id", ondelete="RESTRICT"), nullable=True
    )
    parent_execution_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="RESTRICT"), nullable=True
    )
    root_execution_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="RESTRICT"), nullable=False
    )
    retry_of_execution_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="RESTRICT"), nullable=True
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    kind: Mapped[ExecutionKind] = mapped_column(String(32), nullable=False)
    capability_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    capability_version: Mapped[Optional[str]] = mapped_column(
        String(128), nullable=True
    )
    flow_version_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("flow_versions.id", ondelete="RESTRICT"), nullable=True
    )
    flow_node_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    initiated_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    extension_installation_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID,
        ForeignKey("extension_installations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[ExecutionStatus] = mapped_column(
        String(32), nullable=False, default=ExecutionStatus.queued
    )
    waiting_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    input: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    output_summary: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deadline_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancellation_requested_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trace_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    error_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    thread: Mapped[Optional[Thread]] = relationship("Thread", back_populates="executions")
    turn: Mapped[Optional[Turn]] = relationship("Turn", back_populates="executions")
    course: Mapped[Optional["Course"]] = relationship(
        "Course", back_populates="executions"
    )
    assignment: Mapped[Optional["Assignment"]] = relationship(
        "Assignment", back_populates="executions"
    )
    submissions: Mapped[list["Submission"]] = relationship(
        "Submission",
        secondary="execution_submissions",
        back_populates="executions",
    )
    parent = relationship(
        "Execution", foreign_keys=[parent_execution_id], remote_side=[id]
    )
    root = relationship("Execution", foreign_keys=[root_execution_id], remote_side=[id])
    retry_of = relationship(
        "Execution", foreign_keys=[retry_of_execution_id], remote_side=[id]
    )
    flow_version = relationship("FlowVersion", back_populates="executions")
    events: Mapped[list["ExecutionEvent"]] = relationship(
        "ExecutionEvent", back_populates="execution", cascade="all, delete-orphan"
    )
    snapshot: Mapped[Optional["ExecutionSnapshot"]] = relationship(
        "ExecutionSnapshot",
        back_populates="execution",
        uselist=False,
        cascade="all, delete-orphan",
    )
    interaction_requests: Mapped[list["InteractionRequest"]] = relationship(
        "InteractionRequest", back_populates="execution", cascade="all, delete-orphan"
    )
    messages: Mapped[list["Message"]] = relationship(
        "Message", back_populates="producing_execution"
    )
    dispatches: Mapped[list["ExecutionDispatchOutbox"]] = relationship(
        "ExecutionDispatchOutbox", back_populates="execution", cascade="all, delete-orphan"
    )


class ExecutionEvent(Base):
    __tablename__ = "execution_events"
    __table_args__ = (
        UniqueConstraint(
            "execution_id", "sequence", name="uq_execution_events_execution_sequence"
        ),
        UniqueConstraint(
            "producer_source",
            "producer_event_id",
            name="uq_execution_events_producer_identity",
        ),
        Index("ix_execution_events_replay", "execution_id", "sequence"),
        Index("ix_execution_events_type_time", "execution_id", "type", "occurred_at"),
        Index("ix_execution_events_trace", "trace_id"),
        CheckConstraint("sequence >= 1", name="ck_execution_events_sequence_positive"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(BigInteger, nullable=False)
    producer_source: Mapped[str] = mapped_column(String(255), nullable=False)
    producer_event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    producer_sequence: Mapped[Optional[int]] = mapped_column(
        BigInteger, nullable=True
    )
    type: Mapped[str] = mapped_column(String(255), nullable=False)
    schema_uri: Mapped[str] = mapped_column(String(2048), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    visibility: Mapped[EventVisibility] = mapped_column(
        String(32), nullable=False, default=EventVisibility.user
    )
    durability: Mapped[EventDurability] = mapped_column(
        String(32), nullable=False, default=EventDurability.durable
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    parent_event_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("execution_events.id", ondelete="RESTRICT"), nullable=True
    )
    trace_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    span_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    execution: Mapped[Execution] = relationship("Execution", back_populates="events")
    parent = relationship("ExecutionEvent", remote_side=[id])


class ExecutionSnapshot(Base):
    __tablename__ = "execution_snapshots"

    execution_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="CASCADE"), primary_key=True
    )
    last_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    reducer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    projection: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    execution: Mapped[Execution] = relationship("Execution", back_populates="snapshot")


class InteractionRequest(Base):
    __tablename__ = "interaction_requests"
    __table_args__ = (
        Index("ix_interaction_requests_execution_status", "execution_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(64), nullable=False)
    schema: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    message: Mapped[str] = mapped_column(Text, nullable=False)
    choices: Mapped[Optional[list[dict[str, Any]]]] = mapped_column(
        json_document_type(), nullable=True
    )
    target_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[InteractionStatus] = mapped_column(
        String(32), nullable=False, default=InteractionStatus.pending
    )
    requested_by_extension_installation_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID,
        ForeignKey("extension_installations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolved_by_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    response: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )

    execution: Mapped[Execution] = relationship(
        "Execution", back_populates="interaction_requests"
    )


class ExecutionDispatchOutbox(Base):
    __tablename__ = "execution_dispatch_outbox"
    __table_args__ = (
        Index("ix_dispatch_outbox_claim", "status", "available_at"),
        UniqueConstraint("job_id", name="uq_dispatch_outbox_job_id"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    execution_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="CASCADE"), nullable=False
    )
    command_kind: Mapped[DispatchCommandKind] = mapped_column(
        String(32), nullable=False
    )
    job_id: Mapped[str] = mapped_column(String(255), nullable=False)
    target: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        json_document_type(), nullable=False, default=dict
    )
    status: Mapped[DispatchStatus] = mapped_column(
        String(32), nullable=False, default=DispatchStatus.pending
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    claimed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dispatched_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    execution: Mapped[Execution] = relationship(
        "Execution", back_populates="dispatches"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("turn_id", "ordinal", name="uq_messages_turn_ordinal"),
        Index("ix_messages_thread_created", "thread_id", "created_at"),
        CheckConstraint("ordinal >= 1", name="ck_messages_ordinal_positive"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    thread_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("threads.id", ondelete="CASCADE"), nullable=False
    )
    turn_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("turns.id", ondelete="CASCADE"), nullable=True
    )
    producing_execution_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("executions.id", ondelete="RESTRICT"), nullable=True
    )
    parent_message_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("messages.id", ondelete="RESTRICT"), nullable=True
    )
    role: Mapped[MessageRole] = mapped_column(String(32), nullable=False)
    author_type: Mapped[MessageAuthorType] = mapped_column(
        String(32), nullable=False
    )
    author_user_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    author_extension_installation_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID,
        ForeignKey("extension_installations.id", ondelete="RESTRICT"),
        nullable=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[MessageStatus] = mapped_column(
        String(32), nullable=False, default=MessageStatus.streaming
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    thread: Mapped[Thread] = relationship("Thread", back_populates="messages")
    turn: Mapped[Optional[Turn]] = relationship("Turn", back_populates="messages")
    producing_execution: Mapped[Optional[Execution]] = relationship(
        "Execution", back_populates="messages"
    )
    parts: Mapped[list["MessagePart"]] = relationship(
        "MessagePart", back_populates="message", cascade="all, delete-orphan",
        order_by="MessagePart.ordinal",
    )


class MessagePart(Base):
    __tablename__ = "message_parts"
    __table_args__ = (
        UniqueConstraint("message_id", "ordinal", name="uq_message_parts_message_ordinal"),
        CheckConstraint("ordinal >= 1", name="ck_message_parts_ordinal_positive"),
    )

    id: Mapped[UUID] = mapped_column(SAUUID, primary_key=True, default=uuid4)
    message_id: Mapped[UUID] = mapped_column(
        SAUUID, ForeignKey("messages.id", ondelete="CASCADE"), nullable=False
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    part_type: Mapped[str] = mapped_column(String(64), nullable=False)
    media_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    schema_uri: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    text_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        json_document_type(), nullable=True
    )
    artifact_version_id: Mapped[Optional[UUID]] = mapped_column(
        SAUUID, ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )

    message: Mapped[Message] = relationship("Message", back_populates="parts")


__all__ = [
    "DispatchCommandKind",
    "DispatchStatus",
    "EventDurability",
    "EventVisibility",
    "Execution",
    "ExecutionDispatchOutbox",
    "ExecutionEvent",
    "ExecutionKind",
    "ExecutionSnapshot",
    "ExecutionStatus",
    "InteractionRequest",
    "InteractionStatus",
    "Message",
    "MessageAuthorType",
    "MessagePart",
    "MessageRole",
    "MessageStatus",
    "Thread",
    "ThreadStatus",
    "Turn",
    "TurnStatus",
]
