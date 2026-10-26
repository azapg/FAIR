from types import SimpleNamespace

from fair_platform.backend.data.migrations import _escape_for_alembic_ini
from fair_platform.backend.data.migrations import build_alembic_config


def test_escape_for_alembic_ini_escapes_percent_signs() -> None:
    raw = "postgresql+psycopg://user:pa%24ss@host:5432/db?sslmode=require"
    escaped = _escape_for_alembic_ini(raw)
    assert escaped == "postgresql+psycopg://user:pa%%24ss@host:5432/db?sslmode=require"


def test_build_alembic_config_preserves_runtime_database_password(monkeypatch) -> None:
    from fair_platform.backend.data import database

    class FakeURL:
        def render_as_string(self, *, hide_password: bool) -> str:
            assert hide_password is False
            return "postgresql://user:secret@host:5432/db"

    monkeypatch.setattr(database, "engine", SimpleNamespace(url=FakeURL()))

    config = build_alembic_config()

    assert config.get_main_option("sqlalchemy.url") == (
        "postgresql+psycopg://user:secret@host:5432/db"
    )


def test_build_alembic_config_normalizes_postgres_alias() -> None:
    config = build_alembic_config("postgres://user:pass@host:5432/db")

    assert config.get_main_option("sqlalchemy.url") == (
        "postgresql+psycopg://user:pass@host:5432/db"
    )
