import typer
from typing_extensions import Annotated
import subprocess
import os

app = typer.Typer()

# --- DB (Alembic) subcommands ---------------------------------------------------------
db_app = typer.Typer(help="Database migration commands (Alembic wrapper)")

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))


def _run_alembic(*args: str):
    if not os.path.isdir(BACKEND_DIR):
        typer.echo("Backend directory not found for Alembic operations", err=True)
        raise typer.Exit(1)
    cmd = ["alembic", *args]
    typer.echo(f"[alembic] {' '.join(args)}")
    try:
        subprocess.run(cmd, cwd=BACKEND_DIR, check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Alembic command failed: {e}", err=True)
        raise typer.Exit(e.returncode)


@db_app.command("upgrade")
def db_upgrade(revision: Annotated[str, typer.Argument(help="Revision to upgrade to (default=head)")] = "head"):
    """Apply migrations up to the given revision (default=head)."""
    _run_alembic("upgrade", revision)


@db_app.command("downgrade")
def db_downgrade(revision: Annotated[str, typer.Argument(help="Revision to downgrade to (e.g. -1, base)")] = "-1"):
    """Downgrade migrations (default one step)."""
    _run_alembic("downgrade", revision)


@db_app.command("revision")
def db_revision(
    message: Annotated[str, typer.Option("-m", "--message", help="Revision message")] = "auto",
    autogenerate: Annotated[bool, typer.Option("--autogenerate", "-a", help="Autogenerate from models")] = True,
):
    """Create a new revision (defaults to --autogenerate)."""
    args = ["revision", "-m", message]
    if autogenerate:
        args.append("--autogenerate")
    _run_alembic(*args)


app.add_typer(db_app, name="db")

# -------------------------------------------------------------------------------------
@app.command()
def serve(port: Annotated[int, typer.Option("--port", "-p", help="Port to run the development server on")] = 3000):
    """Start the Fair Platform development server."""
    # I still have to figure out whether this will work for production
    # As a reference I have open-webui, which installs the frontend-dev in
    # \AppData\Local\Programs\Python\Python311\Lib\site-packages\open_webui
    script_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_path = os.path.join(script_dir, "..", "platform")
    
    if not os.path.exists(frontend_path) or not os.path.isdir(frontend_path):
        typer.echo(f"Error: {frontend_path} directory not found!", err=True)
        raise typer.Exit(1)
    
    typer.echo(f"Starting Fair Platform development server on port {port}...")
    try:
        subprocess.run(["bun", "run", "dev", "--port", str(port)], cwd=frontend_path, check=True)
    except subprocess.CalledProcessError as e:
        typer.echo(f"Error running development server: {e}", err=True)
        raise typer.Exit(1)
    except KeyboardInterrupt:
        typer.echo("\nDevelopment server stopped.")

@app.command()
def upload(file: Annotated[str, typer.Argument(help="The file to upload")]):
    """Upload a file to the Fair Platform."""
    typer.echo(f"Uploading file {file}")

if __name__ == "__main__":
    app()