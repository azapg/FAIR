import typer
from typing_extensions import Annotated

__version__ = "0.1.0"


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
def serve(port: Annotated[int, typer.Option("--port", "-p", help="Port to run the development server on")] = 3000,
          headless: Annotated[bool, typer.Option("--headless", "-h", help="Run in headless mode")] = False):
    from fair_platform.backend.main import run
    run(port=port, headless=headless)


if __name__ == "__main__":
    app()
