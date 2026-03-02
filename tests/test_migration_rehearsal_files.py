from __future__ import annotations

import sqlite3
from pathlib import Path

from alembic.script import ScriptDirectory

from fair_platform.backend.data.migrations import (
    build_alembic_config,
    run_migrations_to_head,
    run_migrations_to_revision,
)


REHEARSAL_OLD_REVISION = "20260203_0003"


def _alembic_head() -> str:
    script = ScriptDirectory.from_config(build_alembic_config("sqlite:///:memory:"))
    return script.get_current_head()


def _read_revision(db_path: Path) -> str:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute("SELECT version_num FROM alembic_version LIMIT 1").fetchone()
    assert row is not None
    return row[0]


def test_upgrade_rehearsal_from_old_revision_to_head(tmp_path: Path) -> None:
    db_path = tmp_path / "rehearsal_old.sqlite"
    database_url = f"sqlite:///{db_path.as_posix()}"

    run_migrations_to_revision(REHEARSAL_OLD_REVISION, database_url)
    assert _read_revision(db_path) == REHEARSAL_OLD_REVISION

    run_migrations_to_head(database_url)
    assert _read_revision(db_path) == _alembic_head()


def test_upgrade_rehearsal_head_to_head_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / "rehearsal_head.sqlite"
    database_url = f"sqlite:///{db_path.as_posix()}"

    run_migrations_to_head(database_url)
    first = _read_revision(db_path)

    run_migrations_to_head(database_url)
    second = _read_revision(db_path)

    assert first == _alembic_head()
    assert second == first


def test_build_alembic_config_skips_runtime_logging_reconfiguration() -> None:
    config = build_alembic_config("sqlite:///:memory:")
    assert config.get_main_option("fair.skip_logging_config") == "1"

