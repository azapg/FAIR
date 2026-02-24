from fair_platform.backend.data.database import get_database_url


def test_get_database_url_normalizes_postgres_aliases(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/fair")
    assert get_database_url() == "postgresql+psycopg://user:pass@localhost:5432/fair"

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/fair")
    assert get_database_url() == "postgresql+psycopg://user:pass@localhost:5432/fair"

