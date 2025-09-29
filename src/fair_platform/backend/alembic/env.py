"""Alembic environment configuration.

Usage:
  cd backend
  alembic upgrade head
  alembic revision --autogenerate -m "message"

The DATABASE_URL environment variable (or .env file) overrides the fallback URL.
"""

from __future__ import annotations
import os
import sys
from logging.config import fileConfig

from alembic import context  # type: ignore
from sqlalchemy import engine_from_config, pool

# Ensure project root (parent of the 'backend' package) is on sys.path
CURRENT_DIR = os.path.abspath(os.path.dirname(__file__))
BACKEND_DIR = os.path.abspath(os.path.join(CURRENT_DIR, ".."))
PROJECT_ROOT = os.path.abspath(os.path.join(BACKEND_DIR, ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv  # type: ignore

load_dotenv()

from fair_platform.backend.data.database import Base, get_database_url  # noqa: E402
import fair_platform.backend.data.models  # noqa: F401,E402  (import models for autogenerate)

config = context.config

_db_url = get_database_url()
# Force relative sqlite paths to project root so all components share the same DB file
if _db_url.startswith("sqlite:///"):
    # Extract path portion
    sqlite_path = _db_url[len("sqlite:///") :]
    if not os.path.isabs(sqlite_path):
        abs_path = os.path.join(PROJECT_ROOT, sqlite_path)
        _db_url = f"sqlite:///{abs_path.replace(os.sep, '/')}"
config.set_main_option("sqlalchemy.url", _db_url)

# Interpret the config file for Python logging. This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Provide metadata for 'autogenerate'
target_metadata = Base.metadata

# --- Helper functions -----------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
