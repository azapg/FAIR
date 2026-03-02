import fair_platform.cli.main as cli_main
from typer.testing import CliRunner
from pathlib import Path
import re


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


class StubBackendProcess:
    def __init__(self, exitcode: int = 0):
        self.exitcode = exitcode

    def is_alive(self) -> bool:
        return False

    def join(self, timeout: float | None = None) -> None:
        return None

    def terminate(self) -> None:
        return None

    def kill(self) -> None:
        return None


class InterruptingBackendProcess(StubBackendProcess):
    def is_alive(self) -> bool:
        raise KeyboardInterrupt


def test_dev_command_runs_backend_only_when_frontend_disabled(monkeypatch):
    runner = CliRunner()
    backend_calls = {}
    stopped = []

    def fail_frontend_start(*_args, **_kwargs):
        raise AssertionError("frontend should not start")

    def start_backend(port: int, headless: bool):
        backend_calls["args"] = (port, headless)
        return StubBackendProcess()

    def stop_backend(process: StubBackendProcess):
        stopped.append(process)

    monkeypatch.setattr(cli_main, "_start_backend_process", start_backend)
    monkeypatch.setattr(cli_main, "_stop_backend", stop_backend)
    monkeypatch.setattr(cli_main, "_get_frontend_dir", lambda: None)
    monkeypatch.setattr(cli_main, "_start_frontend_process", fail_frontend_start)

    result = runner.invoke(cli_main.app, ["dev", "--no-frontend"])

    assert result.exit_code == 0
    assert backend_calls["args"] == (8000, True)
    assert stopped


def test_dev_command_disables_headless_mode_when_flag_set(monkeypatch):
    runner = CliRunner()
    backend_calls = {}

    def start_backend(port: int, headless: bool):
        backend_calls["args"] = (port, headless)
        return StubBackendProcess()

    monkeypatch.setattr(cli_main, "_start_backend_process", start_backend)
    monkeypatch.setattr(cli_main, "_stop_backend", lambda *_: None)
    monkeypatch.setattr(cli_main, "_get_frontend_dir", lambda: None)

    result = runner.invoke(cli_main.app, ["dev", "--no-frontend", "--no-headless"])

    assert result.exit_code == 0
    assert backend_calls["args"] == (8000, False)


def test_serve_command_disables_dev(monkeypatch):
    runner = CliRunner()
    captured = {}

    def fake_run(host: str, port: int, headless: bool, dev: bool):
        captured["args"] = (host, port, headless, dev)

    monkeypatch.setattr(cli_main, "_run_server", fake_run)

    result = runner.invoke(cli_main.app, ["serve", "--no-update-check"])

    assert result.exit_code == 0
    assert captured["args"][3] is False


def test_dev_command_handles_keyboard_interrupt(monkeypatch):
    runner = CliRunner()
    stopped = []
    backend = InterruptingBackendProcess()

    def start_backend(port: int, headless: bool):
        return backend

    def stop_backend(process: StubBackendProcess):
        stopped.append(process)

    monkeypatch.setattr(cli_main, "_start_backend_process", start_backend)
    monkeypatch.setattr(cli_main, "_stop_backend", stop_backend)

    result = runner.invoke(cli_main.app, ["dev", "--no-frontend"])

    assert result.exit_code == 0
    assert backend in stopped


def test_db_upgrade_command_invokes_alembic(monkeypatch):
    runner = CliRunner()
    captured = {}

    def fake_run(action: str, *args, **kwargs):
        captured["action"] = action
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(cli_main, "_run_alembic", fake_run)

    result = runner.invoke(cli_main.app, ["db", "upgrade", "head"])

    assert result.exit_code == 0
    assert captured["action"] == "upgrade"
    assert captured["args"] == ("head",)


def test_db_revision_autogenerate_invokes_alembic(monkeypatch):
    runner = CliRunner()
    captured = {}

    def fake_run(action: str, *args, **kwargs):
        captured["action"] = action
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(cli_main, "_run_alembic", fake_run)

    result = runner.invoke(
        cli_main.app, ["db", "revision", "--autogenerate", "-m", "add something"]
    )

    assert result.exit_code == 0
    assert captured["action"] == "revision"
    assert captured["kwargs"]["autogenerate"] is True
    assert captured["kwargs"]["message"] == "add something"


def test_db_migrate_sqlite_to_postgres_invokes_copy(monkeypatch):
    runner = CliRunner()
    captured = {}

    def fake_migrate(from_sqlite, to_postgres, on_conflict, dry_run, verify):
        captured["from_sqlite"] = from_sqlite
        captured["to_postgres"] = to_postgres
        captured["on_conflict"] = on_conflict
        captured["dry_run"] = dry_run
        captured["verify"] = verify
        return {"users": 1, "courses": 2}

    monkeypatch.setattr(cli_main, "_migrate_sqlite_to_postgres", fake_migrate)

    result = runner.invoke(
        cli_main.app,
        [
            "db",
            "migrate-sqlite-to-postgres",
            "--from-sqlite",
            "new.db",
            "--to-postgres",
            "postgresql://postgres:postgres@localhost:55432/postgres",
            "--on-conflict",
            "skip",
            "--dry-run",
            "--verify",
        ],
    )

    assert result.exit_code == 0
    assert captured["from_sqlite"] == Path("new.db")
    assert captured["to_postgres"] == "postgresql://postgres:postgres@localhost:55432/postgres"
    assert captured["on_conflict"] == "skip"
    assert captured["dry_run"] is True
    assert captured["verify"] is True


def test_db_migrate_sqlite_to_postgres_requires_target():
    runner = CliRunner()
    result = runner.invoke(
        cli_main.app,
        ["db", "migrate-sqlite-to-postgres", "--from-sqlite", "new.db"],
    )
    assert result.exit_code != 0
    clean = _strip_ansi(result.output).replace("\n", " ")
    assert "Missing option" in clean
    assert "--to-postgres" in clean


def test_db_migrate_sqlite_to_postgres_rejects_invalid_conflict_mode():
    runner = CliRunner()
    result = runner.invoke(
        cli_main.app,
        [
            "db",
            "migrate-sqlite-to-postgres",
            "--from-sqlite",
            "new.db",
            "--to-postgres",
            "postgresql://postgres:postgres@localhost:55432/postgres",
            "--on-conflict",
            "replace",
        ],
    )
    assert result.exit_code != 0
    assert "on-conflict must be one of: error, skip" in result.output
