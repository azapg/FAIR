"""Utility functions for Pydantic schemas."""


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


__all__ = ["to_camel_case"]
