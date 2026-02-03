import multiprocessing
import subprocess
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import tomllib
import typer
from typing_extensions import Annotated


def _get_version() -> str:
    try:
        return version("fair-platform")
    except PackageNotFoundError:
        path = Path(__file__).resolve()
        for parent in path.parents:
            candidate = parent / "pyproject.toml"
            if candidate.exists():
                try:
                    with candidate.open("rb") as f:
                        data = tomllib.load(f)
                    return data.get("project", {}).get("version", "0.0.0")
                except Exception:
                    break
        return "0.0.0"


__version__ = _get_version()


def _run_backend(port: int, headless: bool) -> None:
    _run_server(host="127.0.0.1", port=port, headless=headless, dev=True, serve_docs=False)


def _get_frontend_dir() -> Path:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        frontend_dir = candidate / "frontend-dev"
        if frontend_dir.is_dir():
            return frontend_dir
    typer.echo(
        "Error: Unable to locate frontend-dev directory. Run from the repo root or use --no-frontend."
    )
    raise typer.Exit(code=1)


def _determine_exit_code(
    backend_process: multiprocessing.Process, frontend_process: subprocess.Popen | None
) -> int:
    backend_code = backend_process.exitcode
    if backend_code is None:
        backend_code = 0
    if backend_code != 0:
        return backend_code
    if frontend_process and frontend_process.returncode:
        return frontend_process.returncode
    return 0


def _run_server(host: str, port: int, headless: bool, dev: bool, serve_docs: bool) -> None:
    from fair_platform.backend.main import run

    run(host=host, port=port, headless=headless, dev=dev, serve_docs=serve_docs)


def _start_backend_process(port: int, headless: bool) -> multiprocessing.Process:
    ctx = multiprocessing.get_context("spawn")
    process = ctx.Process(target=_run_backend, kwargs={"port": port, "headless": headless})
    process.start()
    return process


def _start_frontend_process(frontend_dir: Path) -> subprocess.Popen:
    try:
        return subprocess.Popen(["bun", "dev"], cwd=frontend_dir)
    except FileNotFoundError as exc:
        typer.echo(
            "Error: bun is required to run the frontend dev server. Install Bun from https://bun.sh."
        )
        raise typer.Exit(code=1) from exc


def _stop_backend(process: multiprocessing.Process) -> None:
    if process.is_alive():
        process.terminate()
        process.join(timeout=5)
    if process.is_alive():
        process.kill()
        process.join(timeout=5)


def _stop_frontend(process: subprocess.Popen) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def version_callback(value: bool):
    if value:
        typer.echo(f"Running The Fair Platform CLI v{__version__}")
        raise typer.Exit()


app = typer.Typer()


@app.callback()
def common(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback),
):
    pass


@app.command()
def serve(
    port: Annotated[
        int, typer.Option("--port", "-p", help="Port to run the development server on")
    ] = 3000,
    headless: Annotated[
        bool, typer.Option("--headless", "-h", help="Run in headless mode")
    ] = False,
    no_update_check: Annotated[
        bool, typer.Option("--no-update-check", help="Disable version update check")
    ] = False,
    docs: Annotated[
        bool, typer.Option("--docs", help="Serve documentation at /docs endpoint")
    ] = False,
):
    # Check for updates unless disabled
    if not no_update_check:
        from fair_platform.utils.version import check_for_updates
        check_for_updates()
    
    _run_server(host="127.0.0.1", port=port, headless=headless, dev=False, serve_docs=docs)


@app.command()
def dev(
    port: Annotated[int, typer.Option("--port", "-p", help="Backend port to use")] = 8000,
    no_frontend: Annotated[
        bool, typer.Option("--no-frontend", help="Disable frontend dev server")
    ] = False,
    no_headless: Annotated[
        bool,
        typer.Option("--no-headless", help="Serve the bundled frontend from the backend"),
    ] = False,
):
    frontend_process = None
    backend_process = _start_backend_process(port=port, headless=not no_headless)

    try:
        if not no_frontend:
            frontend_dir = _get_frontend_dir()
            frontend_process = _start_frontend_process(frontend_dir)

        while True:
            if not backend_process.is_alive():
                break
            if frontend_process and frontend_process.poll() is not None:
                break
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        if frontend_process:
            _stop_frontend(frontend_process)
        _stop_backend(backend_process)

    raise typer.Exit(code=_determine_exit_code(backend_process, frontend_process))


if __name__ == "__main__":
    app()
