import pytest

import fair_platform.backend.main as backend_main


def test_auto_migrate_enabled_by_default(monkeypatch):
    monkeypatch.delenv("FAIR_AUTO_MIGRATE", raising=False)
    assert backend_main._is_auto_migrate_enabled() is True


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", " Yes "])
def test_auto_migrate_enabled_truthy_values(monkeypatch, value: str):
    monkeypatch.setenv("FAIR_AUTO_MIGRATE", value)
    assert backend_main._is_auto_migrate_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", " FALSE "])
def test_auto_migrate_disabled_values(monkeypatch, value: str):
    monkeypatch.setenv("FAIR_AUTO_MIGRATE", value)
    assert backend_main._is_auto_migrate_enabled() is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", " TRUE "])
def test_create_all_fallback_enabled_values(monkeypatch, value: str):
    monkeypatch.setenv("FAIR_ALLOW_CREATE_ALL", value)
    assert backend_main._is_create_all_fallback_enabled() is True


@pytest.mark.parametrize("value", ["0", "false", "no", "off", " FALSE ", ""])
def test_create_all_fallback_disabled_values(monkeypatch, value: str):
    monkeypatch.setenv("FAIR_ALLOW_CREATE_ALL", value)
    assert backend_main._is_create_all_fallback_enabled() is False


@pytest.mark.asyncio
async def test_lifespan_runs_migrations_when_enabled(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(backend_main, "_is_auto_migrate_enabled", lambda: True)
    monkeypatch.setattr(
        backend_main, "run_migrations_to_head", lambda: calls.append("migrate")
    )
    monkeypatch.setattr(backend_main, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(
        backend_main, "load_storage_plugins", lambda: calls.append("plugins")
    )

    async with backend_main.lifespan(backend_main.app):
        pass

    assert calls == ["migrate", "plugins"]


@pytest.mark.asyncio
async def test_lifespan_runs_init_db_when_explicitly_enabled(monkeypatch):
    calls: list[str] = []

    monkeypatch.setattr(backend_main, "_is_auto_migrate_enabled", lambda: False)
    monkeypatch.setattr(backend_main, "_is_create_all_fallback_enabled", lambda: True)
    monkeypatch.setattr(
        backend_main, "run_migrations_to_head", lambda: calls.append("migrate")
    )
    monkeypatch.setattr(backend_main, "init_db", lambda: calls.append("init_db"))
    monkeypatch.setattr(
        backend_main, "load_storage_plugins", lambda: calls.append("plugins")
    )

    async with backend_main.lifespan(backend_main.app):
        pass

    assert calls == ["init_db", "plugins"]


@pytest.mark.asyncio
async def test_lifespan_raises_when_no_migration_and_no_fallback(monkeypatch):
    monkeypatch.setattr(backend_main, "_is_auto_migrate_enabled", lambda: False)
    monkeypatch.setattr(backend_main, "_is_create_all_fallback_enabled", lambda: False)
    monkeypatch.setattr(backend_main, "run_migrations_to_head", lambda: None)
    monkeypatch.setattr(backend_main, "init_db", lambda: None)
    monkeypatch.setattr(backend_main, "load_storage_plugins", lambda: None)

    with pytest.raises(RuntimeError, match="FAIR_AUTO_MIGRATE is disabled"):
        async with backend_main.lifespan(backend_main.app):
            pass
