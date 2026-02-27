from fair_platform.backend.data.migrations import _escape_for_alembic_ini


def test_escape_for_alembic_ini_escapes_percent_signs() -> None:
    raw = "postgresql+psycopg://user:pa%24ss@host:5432/db?sslmode=require"
    escaped = _escape_for_alembic_ini(raw)
    assert escaped == "postgresql+psycopg://user:pa%%24ss@host:5432/db?sslmode=require"

