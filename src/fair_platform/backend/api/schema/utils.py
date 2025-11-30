"""Utility functions and shared configuration for Pydantic schemas."""

from pydantic import ConfigDict
from pydantic.alias_generators import to_camel


# Shared model configuration for all schemas
# Uses ConfigDict (Pydantic V2) with:
# - from_attributes: Enable ORM mode for SQLAlchemy models
# - alias_generator: Convert snake_case to camelCase for frontend (using Pydantic's built-in)
# - validate_by_name: Accept both field names and aliases as input
#   (Note: populate_by_name is deprecated and scheduled for removal in V3)
schema_config = ConfigDict(
    from_attributes=True,
    alias_generator=to_camel,
    validate_by_name=True,
)

# Configuration for schemas that also need enum values serialized
schema_config_with_enum = ConfigDict(
    from_attributes=True,
    alias_generator=to_camel,
    validate_by_name=True,
    use_enum_values=True,
)


__all__ = ["to_camel", "schema_config", "schema_config_with_enum"]
