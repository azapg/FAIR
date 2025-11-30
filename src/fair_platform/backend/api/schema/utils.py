"""Utility functions and shared configuration for Pydantic schemas."""

from pydantic import ConfigDict


def to_camel_case(field_name: str) -> str:
    """
    Convert snake_case field names to camelCase for frontend compatibility.
    
    Args:
        field_name: The field name in snake_case format
        
    Returns:
        The field name in camelCase format
        
    Example:
        >>> to_camel_case("user_id")
        'userId'
        >>> to_camel_case("created_at")
        'createdAt'
    """
    components = field_name.split("_")
    return components[0] + "".join(word.capitalize() for word in components[1:])


# Shared model configuration for all schemas
# Uses ConfigDict (Pydantic V2) with:
# - from_attributes: Enable ORM mode for SQLAlchemy models
# - alias_generator: Convert snake_case to camelCase for frontend
# - validate_by_name: Accept both field names and aliases as input
#   (Note: populate_by_name is deprecated and scheduled for removal in V3)
schema_config = ConfigDict(
    from_attributes=True,
    alias_generator=to_camel_case,
    validate_by_name=True,
)


__all__ = ["to_camel_case", "schema_config"]
