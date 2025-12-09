import typer
from typing_extensions import Annotated
from importlib.metadata import version, PackageNotFoundError
from pathlib import Path
import tomllib


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
    dev: Annotated[
        bool, typer.Option("--dev", "-d", help="Run in development mode")
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
    
    from fair_platform.backend.main import run

    run(host="127.0.0.1", port=port, headless=headless, dev=dev, serve_docs=docs)


if __name__ == "__main__":
    app()
