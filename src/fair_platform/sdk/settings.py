from abc import abstractmethod, ABC
from typing import Optional, TypeVar, Generic

T = TypeVar('T')


class SettingsField(Generic[T], ABC):
    def __init__(self, label: str, default: T, required: bool = False):
        self.label: str = label
        self.default: T = default
        self.required: bool = required

        self.value: T = default

        self.name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name
        if not hasattr(owner, '_config_fields'):
            owner._config_fields = {}
        owner._config_fields[name] = self

    @abstractmethod
    def to_pydantic_field(self):
        pass


class TextField(SettingsField[str]):
    def __init__(self, label: str, default: str, required: bool = False, inline: bool = False,
                 min_length: Optional[int] = 0, max_length: Optional[int] = None, pattern: Optional[str] = None):
        super().__init__(label, default, required)
        self.inline = inline
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern

    def to_pydantic_field(self):
        from pydantic import Field
        return (str, Field(default=self.default, title="TextField", description=self.label,
                           min_length=self.min_length if self.required else 0,
                           max_length=self.max_length, pattern=self.pattern))


class NumberField(SettingsField[float]):
    def __init__(self, label: str, default: float, required: bool = False,
                 ge: Optional[float] = None, le: Optional[float] = None):
        super().__init__(label, default, required)
        self.ge = ge
        self.le = le

    def to_pydantic_field(self):
        from pydantic import Field
        return (float, Field(default=self.default, title="NumberField", description=self.label,
                             ge=self.ge, le=self.le))


class SwitchField(SettingsField[bool]):
    def __init__(self, label: str, default: bool, required: bool = False):
        super().__init__(label, default, required)

    def to_pydantic_field(self):
        from pydantic import Field
        return bool, Field(default=self.default, title="SwitchField", description=self.label)
