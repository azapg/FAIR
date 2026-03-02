from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


contract_model_config = ConfigDict(
    alias_generator=to_camel,
    validate_by_name=True,
    validate_by_alias=True,
)


__all__ = ["contract_model_config", "to_camel"]
