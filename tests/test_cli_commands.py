from typer.testing import CliRunner

import fair_platform.cli.main as cli_main


class DummyBackend:
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


def test_dev_command_no_frontend(monkeypatch):
    runner = CliRunner()
    backend_calls = {}
    stopped = []

    def start_backend(port: int, headless: bool):
        backend_calls["args"] = (port, headless)
        return DummyBackend()

    def stop_backend(process: DummyBackend):
        stopped.append(process)

    monkeypatch.setattr(cli_main, "_start_backend_process", start_backend)
    monkeypatch.setattr(cli_main, "_stop_backend", stop_backend)
    monkeypatch.setattr(cli_main, "_find_frontend_dir", lambda: None)
    monkeypatch.setattr(
        cli_main, "_start_frontend_process", lambda *_: (_ for _ in ()).throw(AssertionError())
    )

    result = runner.invoke(cli_main.app, ["dev", "--no-frontend"])

    assert result.exit_code == 0
    assert backend_calls["args"] == (8000, True)
    assert stopped


def test_dev_command_no_headless(monkeypatch):
    runner = CliRunner()
    backend_calls = {}

    def start_backend(port: int, headless: bool):
        backend_calls["args"] = (port, headless)
        return DummyBackend()

    monkeypatch.setattr(cli_main, "_start_backend_process", start_backend)
    monkeypatch.setattr(cli_main, "_stop_backend", lambda *_: None)
    monkeypatch.setattr(cli_main, "_find_frontend_dir", lambda: None)

    result = runner.invoke(cli_main.app, ["dev", "--no-frontend", "--no-headless"])

    assert result.exit_code == 0
    assert backend_calls["args"] == (8000, False)


def test_serve_command_disables_dev(monkeypatch):
    runner = CliRunner()
    captured = {}

    def fake_run(host: str, port: int, headless: bool, dev: bool, serve_docs: bool):
        captured["args"] = (host, port, headless, dev, serve_docs)

    monkeypatch.setattr(cli_main, "_run_server", fake_run)

    result = runner.invoke(cli_main.app, ["serve", "--no-update-check"])

    assert result.exit_code == 0
    assert captured["args"][3] is False
