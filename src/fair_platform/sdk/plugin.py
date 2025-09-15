from abc import ABC, abstractmethod

from fair_platform.sdk import Submission, SettingsField
from typing import Any, Type, List
from pydantic import BaseModel, create_model


class BasePlugin:
    _settings_fields = dict[str, SettingsField[Any]]

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, '_settings_fields'):
            cls._settings_fields = {}

    def set_values(self, values: dict[str, Any]) -> None:
        settings_fields = getattr(self.__class__, '_settings_fields', {})

        for field in values:
            if field not in settings_fields:
                raise ValueError(f"Unknown settings field: {field}")

        for name, field in settings_fields.items():
            if name in values:
                value = values[name]
                if field.required and value is None:
                    raise ValueError(f"Missing required settings field: {name}")
                field.value = value
            else:
                if field.required:
                    raise ValueError(f"Missing required settings field: {name}")

    def create_settings_model(self) -> Type[BaseModel]:
        settings_fields = getattr(self.__class__, '_settings_fields', {})
        model_fields = {}

        for name, field in settings_fields.items():
            field_type, pydantic_field = field.to_pydantic_field()
            model_fields[name] = (field_type, pydantic_field)

        return create_model(f"{self.__class__.__name__}Settings", **model_fields)


class TranscribedSubmission(BaseModel):
    transcription: str
    confidence: float
    original_submission: Submission


class TranscriptionPlugin(BasePlugin, ABC):
    @abstractmethod
    def transcribe(self, submission: Submission) -> TranscribedSubmission:
        pass

    @abstractmethod
    def transcribe_batch(self, submissions: List[Submission]) -> List[TranscribedSubmission]:
        return [self.transcribe(submission=sub) for sub in submissions]


class GradeResult(BaseModel):
    score: float
    feedback: str
    meta: dict[str, Any] = {}


class GradePlugin(BasePlugin, ABC):
    @abstractmethod
    def grade(self, submission: TranscribedSubmission) -> GradeResult:
        pass

    @abstractmethod
    def grade_batch(self, submissions: List[TranscribedSubmission]) -> List[GradeResult]:
        return [self.grade(submission=sub) for sub in submissions]


class ValidationPlugin(BasePlugin, ABC):
    # TODO: I think validation should become "post-processing", but for now
    #  we keep it as is.
    @abstractmethod
    def validate_one(self, grade_result: Any) -> bool:
        pass

    @abstractmethod
    def validate_batch(self, grade_results: List[Any]) -> List[bool]:
        # TODO: What if validate_one is not implemented? Some authors might
        #  only implement batch processing...
        return [self.validate_one(grade_result=gr) for gr in grade_results]
