from abc import abstractmethod, ABC
from typing import Any, Optional, TypeVar, Generic
from pydantic import Field, BaseModel
from fair_platform.sdk.schemas import Artifact, Rubric

T = TypeVar("T")
UNSET = object()


class SettingsField(Generic[T], ABC):
    def __init__(self, label: str, default: Any = UNSET, required: bool = False):
        self.label: str = label
        self.required: bool = required
        self.default: Any = default

        self.value: Any = None if default is UNSET else default

        self.name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        if "_settings_fields" not in owner.__dict__:
            owner._settings_fields = {}
        owner._settings_fields[name] = self

    def pydantic_default(self) -> Any:
        # Required fields should not receive implicit defaults in schema.
        if self.required:
            return ...
        return None if self.default is UNSET else self.default

    @abstractmethod
    def to_pydantic_field(self) -> tuple[type, Any]:
        pass


class TextField(SettingsField[str]):
    def __init__(
        self,
        label: str,
        default: Any = UNSET,
        required: bool = False,
        inline: bool = False,
        min_length: Optional[int] = 0,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
    ):
        super().__init__(label, default, required)
        self.inline = inline
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern

    def to_pydantic_field(self):
        return (
            str,
            Field(
                default=self.pydantic_default(),
                title="TextField",
                description=self.label,
                min_length=self.min_length if self.required else 0,
                max_length=self.max_length,
                pattern=self.pattern,
            ),
        )

class SensitiveTextField(SettingsField[str]):
    def __init__(
        self,
        label: str,
        default: Any = UNSET,
        required: bool = False,
        inline: bool = False,
        min_length: Optional[int] = 0,
        max_length: Optional[int] = None,
        pattern: Optional[str] = None,
    ):
        super().__init__(label, default, required)
        self.inline = inline
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern

    def to_pydantic_field(self):
        return (
            str,
            Field(
                default=self.pydantic_default(),
                title="SensitiveTextField",
                description=self.label,
                min_length=self.min_length if self.required else 0,
                max_length=self.max_length,
                pattern=self.pattern,
            ),
        )

class NumberField(SettingsField[float]):
    def __init__(
        self,
        label: str,
        default: Any = UNSET,
        required: bool = False,
        ge: Optional[float] = None,
        le: Optional[float] = None,
    ):
        super().__init__(label, default, required)
        self.ge = ge
        self.le = le

    def to_pydantic_field(self):
        return (
            float,
            Field(
                default=self.pydantic_default(),
                title="NumberField",
                description=self.label,
                ge=self.ge,
                le=self.le,
            ),
        )


class SwitchField(SettingsField[bool]):
    def __init__(self, label: str, default: Any = UNSET, required: bool = False):
        super().__init__(label, default, required)

    def to_pydantic_field(self):
        return bool, Field(
            default=self.pydantic_default(),
            title="SwitchField",
            description=self.label,
        )


class CheckboxField(SettingsField[bool]):
    def __init__(self, label: str, default: Any = UNSET, required: bool = False):
        super().__init__(label, default, required)

    def to_pydantic_field(self):
        return bool, Field(
            default=self.pydantic_default(),
            title="CheckboxField",
            description=self.label,
        )


class FileInput(BaseModel):
    filename: str
    url: str


class FileField(SettingsField[FileInput]):
    def __init__(
        self,
        label: str,
        default: Optional[FileInput] = None,
        required: bool = False,
        file_types: Optional[list[str]] = None,
    ):
        super().__init__(label, default, required)
        self.file_types = file_types or ["*"]

    def to_pydantic_field(self):
        return FileInput, Field(
            default=self.pydantic_default(),
            title="FileField",
            description=self.label,
        )


class CourseArtifactsSelectorField(SettingsField[Artifact]):
    def __init__(
        self,
        label: str,
        default: Optional[Artifact] = None,
        required: bool = False,
        allowed_mime_types: Optional[list[str]] = None,
    ):
        super().__init__(label, default, required)
        self.allowed_mime_types = allowed_mime_types or []

    def to_pydantic_field(self):
        return (
            Artifact,
            Field(
                default=self.pydantic_default(),
                title="CourseArtifactsSelectorField",
                description=self.label,
                json_schema_extra={
                    "source": "course_artifacts",
                    "selection": "single",
                    "allowed_mime_types": self.allowed_mime_types,
                },
            ),
        )


class RubricField(SettingsField[Rubric]):
    def __init__(
        self,
        label: str,
        default: Optional[Rubric] = None,
        required: bool = False,
    ):
        super().__init__(label, default, required)

    def to_pydantic_field(self):
        return (
            Rubric,
            Field(
                default=self.pydantic_default(),
                title="RubricField",
                description=self.label,
                json_schema_extra={
                    "source": "rubrics",
                    "selection": "single",
                },
            ),
        )


class SliderField(SettingsField[float]):
    def __init__(
        self,
        label: str,
        default: Any = UNSET,
        min: Optional[float] = None,
        max: Optional[float] = None,
        step: Optional[float] = None,
        marks: Optional[dict[float, str]] = None # e.g. {0: "Low", 100: "High"}
    ):
        super().__init__(label, default)
        if min is None or max is None or step is None:
            raise ValueError("SliderField requires min, max, and step.")
        self.min = min
        self.max = max
        self.step = step
        self.marks = marks

    def to_pydantic_field(self):
        return (
            float,
            Field(
                default=self.pydantic_default(),
                title="SliderField",
                description=self.label,
                ge=self.min,
                le=self.max,
                # pyright: ignore[reportCallIssue]
                json_schema_extra={"step": self.step, "marks": self.marks}  # pyright: ignore[reportArgumentType]
            )
        )
