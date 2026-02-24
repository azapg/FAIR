from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest
from alembic.script import ScriptDirectory

from fair_platform.backend.data.migrations import build_alembic_config, run_migrations_to_head


REPO_ROOT = Path(__file__).resolve().parents[1]


def _alembic_head() -> str:
    script = ScriptDirectory.from_config(build_alembic_config("sqlite:///:memory:"))
    return script.get_current_head()


@pytest.mark.parametrize("db_file", ["old.db", "new.db"])
def test_upgrade_rehearsal_for_local_db_files(tmp_path: Path, db_file: str) -> None:
    source = REPO_ROOT / db_file
    if not source.exists():
        pytest.skip(f"{db_file} is not present in repository root")

    target = tmp_path / db_file
    shutil.copy2(source, target)

    database_url = f"sqlite:///{target.as_posix()}"
    run_migrations_to_head(database_url)

    with sqlite3.connect(target) as conn:
        version_row = conn.execute(
            "SELECT version_num FROM alembic_version LIMIT 1"
        ).fetchone()

    assert version_row is not None
    assert version_row[0] == _alembic_head()

