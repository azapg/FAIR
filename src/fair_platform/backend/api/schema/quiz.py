from __future__ import annotations

from datetime import datetime, timezone
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from fair_platform.backend.api.schema.utils import schema_config
from fair_platform.backend.data.models.lms_quiz import (
    QuestionKind,
    QuizAttemptStatus,
    QuizReleasePolicy,
    QuizStatus,
)


class QuestionVersionFields(BaseModel):
    model_config = schema_config

    kind: QuestionKind
    prompt: str = Field(min_length=1, max_length=20_000)
    options: list[str] = Field(default_factory=list, max_length=10)
    correct_option_index: int = Field(ge=0)
    default_points: float = Field(default=1, gt=0, allow_inf_nan=False)
    explanation: str | None = Field(default=None, max_length=20_000)

    @model_validator(mode="after")
    def validate_objective_options(self) -> Self:
        if self.kind == QuestionKind.true_false:
            if self.options and [value.strip().lower() for value in self.options] != [
                "true",
                "false",
            ]:
                raise ValueError(
                    "True/false questions use the fixed True and False options"
                )
            if self.correct_option_index not in {0, 1}:
                raise ValueError("True/false correctOptionIndex must be 0 or 1")
            return self
        normalized = [value.strip() for value in self.options]
        if len(normalized) < 2:
            raise ValueError("Single-choice questions require at least two options")
        if any(not value for value in normalized):
            raise ValueError("Question options cannot be blank")
        if len({value.casefold() for value in normalized}) != len(normalized):
            raise ValueError("Question options must be unique")
        if self.correct_option_index >= len(normalized):
            raise ValueError("correctOptionIndex must identify one supplied option")
        return self


class QuestionCreate(QuestionVersionFields):
    title: str = Field(min_length=1, max_length=255)


class QuestionVersionCreate(QuestionVersionFields):
    pass


class QuestionOptionRead(BaseModel):
    model_config = schema_config

    id: str
    text: str


class QuestionVersionAuthoringRead(BaseModel):
    model_config = schema_config

    id: UUID
    question_id: UUID
    version_number: int
    kind: QuestionKind
    prompt: str
    options: list[QuestionOptionRead] = Field(default_factory=list)
    correct_option_id: str
    default_points: float
    explanation: str | None = None
    created_at: datetime


class QuestionAuthoringRead(BaseModel):
    model_config = schema_config

    id: UUID
    bank_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime
    versions: list[QuestionVersionAuthoringRead] = Field(default_factory=list)


class QuestionBankCreate(BaseModel):
    model_config = schema_config

    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=20_000)


class QuestionBankRead(BaseModel):
    model_config = schema_config

    id: UUID
    course_id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    questions: list[QuestionAuthoringRead] = Field(default_factory=list)


class QuizCreate(BaseModel):
    model_config = schema_config

    section_id: UUID
    title: str = Field(min_length=1, max_length=255)
    instructions: str | None = Field(default=None, max_length=20_000)
    attempt_limit: int = Field(default=1, ge=1, le=100)
    release_policy: QuizReleasePolicy = QuizReleasePolicy.manual
    opens_at: datetime | None = None
    closes_at: datetime | None = None

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        opens_at = self.opens_at
        closes_at = self.closes_at
        if opens_at is not None and opens_at.tzinfo is None:
            opens_at = opens_at.replace(tzinfo=timezone.utc)
        elif opens_at is not None:
            opens_at = opens_at.astimezone(timezone.utc)
        if closes_at is not None and closes_at.tzinfo is None:
            closes_at = closes_at.replace(tzinfo=timezone.utc)
        elif closes_at is not None:
            closes_at = closes_at.astimezone(timezone.utc)
        if opens_at is not None and closes_at is not None and opens_at >= closes_at:
            raise ValueError("closesAt must be later than opensAt")
        return self


class QuizQuestionAdd(BaseModel):
    model_config = schema_config

    question_version_id: UUID
    points: float | None = Field(default=None, gt=0, allow_inf_nan=False)


class QuizQuestionAuthoringRead(BaseModel):
    model_config = schema_config

    id: UUID
    position: int
    points: float
    version: QuestionVersionAuthoringRead


class QuizRead(BaseModel):
    model_config = schema_config

    id: UUID
    course_id: UUID
    course_item_id: UUID
    title: str
    instructions: str | None = None
    status: QuizStatus
    release_policy: QuizReleasePolicy
    attempt_limit: int
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    published_at: datetime | None = None
    closed_at: datetime | None = None
    question_count: int
    max_points: float
    created_at: datetime
    updated_at: datetime


class QuizAuthoringRead(QuizRead):
    questions: list[QuizQuestionAuthoringRead] = Field(default_factory=list)


class AttemptQuestionRead(BaseModel):
    model_config = schema_config

    id: UUID
    question_version_id: UUID
    position: int
    kind: QuestionKind
    prompt: str
    options: list[QuestionOptionRead] = Field(default_factory=list)
    points: float
    selected_option_id: str | None = None
    is_correct: bool | None = None
    points_awarded: float | None = None


class QuizAttemptRead(BaseModel):
    model_config = schema_config

    id: UUID
    quiz_id: UUID
    user_id: UUID
    attempt_number: int
    status: QuizAttemptStatus
    max_points: float
    earned_points: float | None = None
    started_at: datetime
    submitted_at: datetime | None = None
    released_at: datetime | None = None
    questions: list[AttemptQuestionRead] = Field(default_factory=list)


class QuizAnswerUpsert(BaseModel):
    model_config = schema_config

    selected_option_id: str = Field(min_length=1, max_length=64)


__all__ = [
    "AttemptQuestionRead",
    "QuestionAuthoringRead",
    "QuestionBankCreate",
    "QuestionBankRead",
    "QuestionCreate",
    "QuestionOptionRead",
    "QuestionVersionAuthoringRead",
    "QuestionVersionCreate",
    "QuizAnswerUpsert",
    "QuizAttemptRead",
    "QuizAuthoringRead",
    "QuizCreate",
    "QuizQuestionAdd",
    "QuizQuestionAuthoringRead",
    "QuizRead",
]
