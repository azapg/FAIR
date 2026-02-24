from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config


def _resolve_alembic_ini_path() -> Path | None:
    candidates = [Path.cwd(), *Path(__file__).resolve().parents]
    for base in candidates:
        repo_ini = base / "alembic.ini"
        if repo_ini.is_file():
            return repo_ini
        legacy_ini = base / "src" / "fair_platform" / "backend" / "alembic.ini"
        if legacy_ini.is_file():
            return legacy_ini
    return None


def build_alembic_config() -> Config:
    import fair_platform.backend as backend_pkg

    config_path = _resolve_alembic_ini_path()
    config = Config(str(config_path)) if config_path else Config()

    backend_dir = Path(backend_pkg.__file__).resolve().parent
    config.set_main_option("script_location", str((backend_dir / "alembic").as_posix()))
    config.set_main_option("sqlalchemy.url", "sqlite:///fair.db")
    return config


def run_migrations_to_head() -> None:
    command.upgrade(build_alembic_config(), "head")
