import multiprocessing
import subprocess
import tomllib
import json
import sqlite3
from collections import OrderedDict
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import typer
from typing_extensions import Annotated
from fair_platform.backend.data.migrations import build_alembic_config


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
_PROCESS_POLL_INTERVAL_SECONDS = 0.5
_DATA_TABLE_ORDER = [
    "users",
    "plugins",
    "courses",
    "submitters",
    "assignments",
    "workflows",
    "artifacts",
    "workflow_runs",
    "submissions",
    "enrollments",
    "rubrics",
    "assignment_artifacts",
    "submission_artifacts",
    "submission_workflow_runs",
    "submission_results",
    "submission_events",
]


def _run_backend(port: int, headless: bool) -> None:
    _run_server(host="127.0.0.1", port=port, headless=headless, dev=True, serve_docs=False)


def _get_frontend_dir() -> Path | None:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for candidate in candidates:
        frontend_dir = candidate / "frontend-dev"
        if frontend_dir.is_dir():
            return frontend_dir
    return None


def _determine_exit_code(
    backend_process: multiprocessing.Process, frontend_process: subprocess.Popen | None
) -> int:
    backend_code = backend_process.exitcode
    if backend_code is None:
        backend_code = 0
    if backend_code != 0:
        return backend_code
    if frontend_process and frontend_process.returncode is not None:
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
db_app = typer.Typer(help="Manage database migrations")
app.add_typer(db_app, name="db")


@app.callback()
def common(
    ctx: typer.Context,
    version: bool = typer.Option(None, "--version", "-v", callback=version_callback),
):
    pass


def _run_alembic(action: str, *args, **kwargs) -> None:
    from alembic import command

    config = build_alembic_config()
    action_fn = getattr(command, action)
    action_fn(config, *args, **kwargs)


@db_app.command("upgrade")
def db_upgrade(
    revision: Annotated[str, typer.Argument(help="Target revision")] = "head",
):
    _run_alembic("upgrade", revision)


@db_app.command("downgrade")
def db_downgrade(
    revision: Annotated[str, typer.Argument(help="Target revision")] = "-1",
):
    _run_alembic("downgrade", revision)


@db_app.command("stamp")
def db_stamp(
    revision: Annotated[str, typer.Argument(help="Revision to stamp")] = "head",
):
    _run_alembic("stamp", revision)


@db_app.command("current")
def db_current(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed revision info")
    ] = False,
):
    _run_alembic("current", verbose=verbose)


@db_app.command("history")
def db_history(
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show detailed revision info")
    ] = False,
):
    _run_alembic("history", verbose=verbose)


@db_app.command("revision")
def db_revision(
    message: Annotated[
        str, typer.Option("--message", "-m", help="Revision message")
    ] = "auto migration",
    autogenerate: Annotated[
        bool, typer.Option("--autogenerate", help="Autogenerate migration from models")
    ] = False,
):
    _run_alembic("revision", message=message, autogenerate=autogenerate)


@db_app.command("migrate")
def db_migrate():
    """Apply all migrations (alias for `fair db upgrade head`)."""
    _run_alembic("upgrade", "head")


def _normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def _migrate_sqlite_to_postgres(
    from_sqlite: Path,
    to_postgres: str,
    on_conflict: str,
    dry_run: bool,
    verify: bool,
) -> dict[str, int]:
    import psycopg
    from psycopg.types.json import Jsonb

    normalized_target = _normalize_postgres_url(to_postgres)
    if not normalized_target.startswith("postgresql+psycopg://"):
        raise ValueError("target must be a PostgreSQL DSN")
    if not from_sqlite.exists():
        raise ValueError(f"source SQLite file does not exist: {from_sqlite}")

    sqlite_conn = sqlite3.connect(from_sqlite)
    sqlite_conn.row_factory = sqlite3.Row
    migrated: OrderedDict[str, int] = OrderedDict()

    pg_dsn_for_psycopg = normalized_target.replace("postgresql+psycopg://", "postgresql://", 1)
    pg_conn = psycopg.connect(pg_dsn_for_psycopg)
    pg_conn.autocommit = False

    try:
        with pg_conn.cursor() as cur:
            cur.execute(
                """
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                """
            )
            pg_types = {(r[0], r[1]): r[2] for r in cur.fetchall()}

            existing_tables = {k[0] for k in pg_types.keys()}
            missing_tables = [t for t in _DATA_TABLE_ORDER if t not in existing_tables]
            if missing_tables:
                raise ValueError(
                    "target PostgreSQL schema is missing required tables. "
                    "Run migrations first. Missing: " + ", ".join(missing_tables)
                )

            if not dry_run:
                cur.execute(
                    "TRUNCATE TABLE "
                    + ", ".join(f'"{t}"' for t in _DATA_TABLE_ORDER)
                    + " RESTART IDENTITY CASCADE"
                )

            for table in _DATA_TABLE_ORDER:
                s_cur = sqlite_conn.cursor()
                s_cur.execute(f'SELECT * FROM "{table}"')
                rows = s_cur.fetchall()
                s_cur.close()

                if not rows:
                    migrated[table] = 0
                    continue

                cols = list(rows[0].keys())
                quoted_cols = ", ".join(f'"{c}"' for c in cols)
                placeholders = ", ".join(["%s"] * len(cols))
                insert_sql = f'INSERT INTO "{table}" ({quoted_cols}) VALUES ({placeholders})'
                if on_conflict == "skip":
                    insert_sql += " ON CONFLICT DO NOTHING"

                batch = []
                for row in rows:
                    converted = []
                    for c in cols:
                        v = row[c]
                        dtype = pg_types.get((table, c), "")
                        if v is None:
                            converted.append(None)
                            continue
                        if dtype in ("json", "jsonb"):
                            if isinstance(v, str):
                                try:
                                    parsed = json.loads(v)
                                except json.JSONDecodeError:
                                    parsed = v
                            else:
                                parsed = v
                            converted.append(Jsonb(parsed) if dtype == "jsonb" else parsed)
                        elif dtype == "boolean" and isinstance(v, int):
                            converted.append(bool(v))
                        else:
                            converted.append(v)
                    batch.append(tuple(converted))

                if dry_run:
                    migrated[table] = len(batch)
                else:
                    cur.executemany(insert_sql, batch)
                    migrated[table] = len(batch)

        if dry_run:
            pg_conn.rollback()
        else:
            pg_conn.commit()

        if verify and not dry_run:
            with pg_conn.cursor() as cur:
                for table, expected in migrated.items():
                    cur.execute(f'SELECT COUNT(*) FROM "{table}"')
                    got = cur.fetchone()[0]
                    if on_conflict == "error" and got != expected:
                        raise RuntimeError(
                            f"verification failed for {table}: expected {expected}, got {got}"
                        )

        return dict(migrated)
    finally:
        sqlite_conn.close()
        pg_conn.close()


@db_app.command("migrate-sqlite-to-postgres")
def db_migrate_sqlite_to_postgres(
    from_sqlite: Annotated[
        Path, typer.Option("--from-sqlite", help="Path to source SQLite DB file")
    ] = Path("fair.db"),
    to_postgres: Annotated[
        str, typer.Option("--to-postgres", help="Target PostgreSQL DSN")
    ] = ...,
    on_conflict: Annotated[
        str, typer.Option("--on-conflict", help="error|skip conflict handling")
    ] = "error",
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Parse and validate rows, but do not persist")
    ] = False,
    verify: Annotated[
        bool, typer.Option("--verify", help="Validate destination row counts after copy")
    ] = False,
):
    if on_conflict not in {"error", "skip"}:
        raise typer.BadParameter("on-conflict must be one of: error, skip")

    typer.echo(f"Starting sqlite -> postgres migration from {from_sqlite} ...")
    summary = _migrate_sqlite_to_postgres(
        from_sqlite=from_sqlite,
        to_postgres=to_postgres.strip(),
        on_conflict=on_conflict,
        dry_run=dry_run,
        verify=verify,
    )

    typer.echo("Migration summary:")
    for table, count in summary.items():
        typer.echo(f"  {table}: {count}")


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
            if frontend_dir is None:
                typer.echo(
                    "Error: Unable to locate frontend-dev directory. Run from the repo root or use --no-frontend."
                )
                raise typer.Exit(code=1)
            frontend_process = _start_frontend_process(frontend_dir)

        while backend_process.is_alive():
            frontend_status = frontend_process.poll() if frontend_process else None
            if frontend_status is not None:
                break
            backend_process.join(timeout=_PROCESS_POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        pass
    finally:
        if frontend_process:
            _stop_frontend(frontend_process)
        _stop_backend(backend_process)

    raise typer.Exit(code=_determine_exit_code(backend_process, frontend_process))


if __name__ == "__main__":
    app()
