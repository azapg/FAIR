from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB


def json_document_type():
    """Use JSON generally, but upgrade to JSONB on PostgreSQL."""
    return JSON().with_variant(JSONB, "postgresql")

