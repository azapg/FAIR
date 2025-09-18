from abc import ABC, abstractmethod

from fair_platform.sdk import Submission, SettingsField
from typing import Any, Type, List, Optional, Dict
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


class PluginMeta(BaseModel):
    name: str
    author: str
    description: Optional[str] = None
    version: Optional[str] = None
    # plugin: Type[BasePlugin]


PLUGINS: Dict[str, PluginMeta] = {}
TRANSCRIPTION_PLUGINS: Dict[str, PluginMeta] = {}
GRADE_PLUGINS: Dict[str, PluginMeta] = {}
VALIDATION_PLUGINS: Dict[str, PluginMeta] = {}


class FairPlugin:
    def __init__(self, name: str, author: str, description: Optional[str] = None, version: Optional[str] = None):
        self.name = name
        self.author = author
        self.description = description
        self.version = version

    def __call__(self, cls: Type[BasePlugin]):
        if not issubclass(cls, BasePlugin):
            raise TypeError("FairPlugin decorator can only be applied to subclasses of BasePlugin")

        # TODO: Later on, plugin uniqueness should be checked via hashes
        if self.name in PLUGINS:
            raise ValueError(f"A plugin with the name '{self.name}' is already registered.")

        metadata = PluginMeta(
            name=self.name,
            author=self.author,
            description=self.description,
            version=self.version,
            # plugin=cls
        )

        PLUGINS[self.name] = metadata

        if issubclass(cls, TranscriptionPlugin):
            TRANSCRIPTION_PLUGINS[self.name] = metadata
        if issubclass(cls, GradePlugin):
            GRADE_PLUGINS[self.name] = metadata
        if issubclass(cls, ValidationPlugin):
            VALIDATION_PLUGINS[self.name] = metadata

        return cls


def get_plugin_metadata(name: str) -> Optional[PluginMeta]:
    return PLUGINS.get(name)


def list_plugins() -> List[PluginMeta]:
    return list(PLUGINS.values())


def list_transcription_plugins() -> List[PluginMeta]:
    return list(TRANSCRIPTION_PLUGINS.values())


def list_grade_plugins() -> List[PluginMeta]:
    return list(GRADE_PLUGINS.values())


def list_validation_plugins() -> List[PluginMeta]:
    return list(VALIDATION_PLUGINS.values())


__all__ = [
    "BasePlugin",
    "TranscriptionPlugin",
    "GradePlugin",
    "ValidationPlugin",

    "TranscribedSubmission",
    "GradeResult",

    "PluginMeta",
    "FairPlugin",
    "get_plugin_metadata",
    "list_plugins",
    "list_transcription_plugins",
    "list_grade_plugins",
    "list_validation_plugins",
]
