import typer
from typing_extensions import Annotated
import subprocess
import os

app = typer.Typer()

@app.command()
def serve(port: Annotated[int, typer.Option("--port", "-p", help="Port to run the development server on")] = 3000):
    """Start the Fair Platform development server."""
    # I still have to figure out whether this will work for production
    # As a reference I have open-webui, which installs the frontend in
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