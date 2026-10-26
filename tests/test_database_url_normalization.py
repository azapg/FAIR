import pytest

from fair_platform.backend.data.database import get_database_url, normalize_database_url


@pytest.mark.parametrize(
    ("raw_url", "expected_url"),
    [
        (
            "postgres://user:pass@localhost:5432/fair",
            "postgresql+psycopg://user:pass@localhost:5432/fair",
        ),
        (
            "postgresql://user:pass@localhost:5432/fair",
            "postgresql+psycopg://user:pass@localhost:5432/fair",
        ),
        ("sqlite:///fair.db", "sqlite:///fair.db"),
    ],
)
def test_normalize_database_url(raw_url, expected_url):
    assert normalize_database_url(raw_url) == expected_url


def test_get_database_url_normalizes_postgres_aliases(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgres://user:pass@localhost:5432/fair")
    assert get_database_url() == "postgresql+psycopg://user:pass@localhost:5432/fair"

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/fair")
    assert get_database_url() == "postgresql+psycopg://user:pass@localhost:5432/fair"
