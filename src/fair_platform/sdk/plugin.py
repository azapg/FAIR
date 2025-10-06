import inspect
from abc import ABC, abstractmethod
from enum import Enum

from fair_platform.sdk import Submission, SettingsField
from typing import Any, Type, List, Optional, Dict, Union
from pydantic import BaseModel, create_model

from fair_platform.sdk.logger import ExtensionLogger


class BasePlugin:
    _settings_fields: dict[str, SettingsField[Any]]

    def __init__(self, logger: Optional[ExtensionLogger]) -> None:
        if logger:
            self.logger = logger
        else:
            self.logger = ExtensionLogger(
                identifier=self.__class__.__name__, bus=None, _mode="debug"
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
    original_submission: Submission


class TranscriptionPlugin(BasePlugin, ABC):
    @abstractmethod
    def transcribe(self, submission: Submission) -> TranscribedSubmission:
        pass

    @abstractmethod
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
    def grade(self, submission: TranscribedSubmission) -> GradeResult:
        pass

    @abstractmethod
    def grade_batch(
        self, submissions: List[TranscribedSubmission]
    ) -> List[GradeResult]:
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

        metadata = PluginMeta(
            id=self.id,
            name=self.name,
            author=self.author,
            description=self.description,
            version=self.version,
            hash=extension_hash,
            source=source,
            author_email=self.author_email,
            settings_schema=create_settings_model(cls).model_json_schema(),
            type=plugin_type,
        )

        PLUGINS[self.name] = metadata
        PLUGINS_OBJECTS[self.name] = cls
        return cls


def get_plugin_metadata(name: str) -> Optional[PluginMeta]:
    return PLUGINS.get(name)


def get_plugin_object(
    name: str,
) -> Optional[
    Union[Type[TranscriptionPlugin], Type[GradePlugin], Type[ValidationPlugin]]
]:
    return PLUGINS_OBJECTS.get(name)


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
    "TranscribedSubmission",
    "GradeResult",
    "PluginMeta",
    "FairPlugin",
    "get_plugin_metadata",
    "get_plugin_object",
    "list_plugins",
    "PluginType",
]
