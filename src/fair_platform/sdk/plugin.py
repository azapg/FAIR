import inspect
from abc import ABC, abstractmethod
from enum import Enum

from fair_platform.backend.data.database import get_session
from fair_platform.backend.data.models import Plugin
from fair_platform.sdk import Submission, SettingsField
from typing import Any, Type, List, Optional, Dict, Union, Tuple
from pydantic import BaseModel, create_model

from fair_platform.sdk.events import DebugEventBus
from fair_platform.sdk.logger import PluginLogger


class BasePlugin:
    _settings_fields: dict[str, SettingsField[Any]]

    def __init__(self, logger: Optional[PluginLogger]) -> None:
        if logger:
            self.logger = logger
        else:
            self.logger = PluginLogger(
                identifier=self.__class__.__name__,
                session_id="debug",
                bus=DebugEventBus(),
            )

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "_settings_fields"):
            cls._settings_fields = {}

    def set_values(self, values: dict[str, Any]) -> None:
        settings_fields = getattr(self.__class__, "_settings_fields", {})

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


def create_settings_model(
    plugin_class: Type[BasePlugin] | BasePlugin,
) -> Type[BaseModel]:
    settings_fields = getattr(plugin_class, "_settings_fields", {})
    model_fields = {}

    for name, field in settings_fields.items():
        field_type, pydantic_field = field.to_pydantic_field()
        model_fields[name] = (field_type, pydantic_field)

    if isinstance(plugin_class, BasePlugin):
        model_name = f"{plugin_class.__class__.__name__}"
    else:
        model_name = plugin_class.__name__

    return create_model(model_name, **model_fields)


class TranscribedSubmission(BaseModel):
    transcription: str
    confidence: float


class TranscriptionPlugin(BasePlugin, ABC):
    @abstractmethod
    def transcribe(self, submission: Submission) -> TranscribedSubmission:
        pass

    def transcribe_batch(
        self, submissions: List[Submission]
    ) -> List[TranscribedSubmission]:
        return [self.transcribe(submission=sub) for sub in submissions]


class GradeResult(BaseModel):
    score: float
    feedback: str
    meta: dict[str, Any] = {}


class GradePlugin(BasePlugin, ABC):
    @abstractmethod
    def grade(
        self, transcribed: TranscribedSubmission, original: Submission
    ) -> GradeResult:
        pass

    def grade_batch(
        self, submissions: List[Tuple[TranscribedSubmission, Submission]]
    ) -> List[GradeResult]:
        return [self.grade(*sub) for sub in submissions]


class ValidationResult(BaseModel):
    is_valid: bool
    modified_score: Optional[float] = None
    modified_feedback: Optional[str] = None
    validation_notes: Optional[str] = None
    meta: dict[str, Any] = {}


class ValidationPlugin(BasePlugin, ABC):
    # TODO: I think validation should become "post-processing", but for now
    #  we keep it as is.
    @abstractmethod
    def validate_one(
        self,
        original: "Submission",
        transcribed: "TranscribedSubmission",
        grade_result: "GradeResult",
    ) -> "ValidationResult":
        pass

    def validate_batch(
        self,
        items: List[Tuple["Submission", "TranscribedSubmission", "GradeResult"]],
    ) -> List["ValidationResult"]:
        return [self.validate_one(*item) for item in items]


class PluginType(str, Enum):
    transcriber = "transcriber"
    grader = "grader"
    validator = "validator"


class PluginMeta(BaseModel):
    id: str
    name: str
    author: str
    author_email: Optional[str] = None
    description: Optional[str] = None
    version: str
    hash: str
    source: str
    settings_schema: Dict[str, Any]
    type: PluginType


PLUGINS: Dict[str, PluginMeta] = {}

PLUGINS_OBJECTS: Dict[
    str, Union[Type[TranscriptionPlugin], Type[GradePlugin], Type[ValidationPlugin]]
] = {}


class FairPlugin:
    def __init__(
        self,
        id: str,
        name: str,
        author,
        version: str,
        description: Optional[str] = None,
        email: Optional[str] = None,
    ):
        self.id = id
        self.name = name
        self.author = author
        self.description = description
        self.author_email = email
        self.version = version

    def __call__(self, cls: Type[BasePlugin]):
        if not issubclass(cls, BasePlugin):
            raise TypeError(
                "FairPlugin decorator can only be applied to subclasses of BasePlugin"
            )

        # TODO: Later on, plugin uniqueness should be checked via hashes
        if self.name in PLUGINS:
            raise ValueError(
                f"A plugin with the name '{self.name}' is already registered."
            )

        current_module = inspect.getmodule(cls)
        extension_hash = getattr(current_module, "__extension_hash__", None)
        if extension_hash is None:
            raise ValueError(
                f"Plugin class '{cls.__name__}' is missing '__extension_hash__' attribute."
            )

        source = getattr(current_module, "__extension_dir__", None)
        if source is None:
            raise ValueError(
                f"Plugin class '{cls.__name__}' is missing '__extension_dir__' attribute."
            )

        if issubclass(cls, TranscriptionPlugin):
            plugin_type = PluginType.transcriber
        elif issubclass(cls, GradePlugin):
            plugin_type = PluginType.grader
        elif issubclass(cls, ValidationPlugin):
            plugin_type = PluginType.validator
        else:
            raise TypeError(
                "FairPlugin decorator can only be applied to subclasses of TranscriptionPlugin, GradePlugin, or ValidationPlugin"
            )

        plugin_args = {
            "id": self.id,
            "name": self.name,
            "author": self.author,
            "description": self.description,
            "version": self.version,
            "hash": extension_hash,
            "source": source,
            "author_email": self.author_email,
            "settings_schema": create_settings_model(cls).model_json_schema(),
            "type": plugin_type,
        }

        plugin = Plugin(**plugin_args)
        runtime_plugin = PluginMeta(**plugin_args)

        # TODO: Bruh, this technically means that extensions can write to the DB
        #  directly. Until this is fully sandboxed, FAIR shouldn't be marked as production-ready.
        with get_session() as session:
            merged_plugin = session.merge(plugin)
            session.commit()
            session.refresh(merged_plugin)

        # TODO: Replace id with hash. For now, this is fine to avoid changing workflows schema.
        PLUGINS[self.id] = runtime_plugin
        PLUGINS_OBJECTS[self.id] = cls
        return cls


def get_plugin_metadata(id: str) -> Optional[PluginMeta]:
    return PLUGINS.get(id)


def get_plugin_object(
    id: str,
) -> Optional[
    Union[Type[TranscriptionPlugin], Type[GradePlugin], Type[ValidationPlugin]]
]:
    return PLUGINS_OBJECTS.get(id)


def list_plugins(plugin_type: Optional[PluginType] = None) -> List[PluginMeta]:
    if plugin_type:
        return [plugin for plugin in PLUGINS.values() if plugin.type == plugin_type]
    return list(PLUGINS.values())


__all__ = [
    "BasePlugin",
    "create_settings_model",
    "TranscriptionPlugin",
    "GradePlugin",
    "ValidationPlugin",
    "ValidationResult",
    "TranscribedSubmission",
    "GradeResult",
    "PluginMeta",
    "FairPlugin",
    "get_plugin_metadata",
    "get_plugin_object",
    "list_plugins",
    "PluginType",
]
