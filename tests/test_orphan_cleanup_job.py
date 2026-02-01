import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from fair_platform.backend.data.models.artifact import Artifact, ArtifactStatus
from fair_platform.backend.jobs.orphan_cleanup import run_orphan_cleanup_once


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"test")


def test_orphan_cleanup_dry_run_and_apply(test_db, tmp_path: Path):
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now()

    with test_db() as session:
        # Artifact with missing file (should be marked orphaned)
        missing_id = uuid4()
        missing = Artifact(
            id=missing_id,
            title="missing",
            artifact_type="file",
            mime="text/plain",
            storage_path=f"{missing_id}/missing.txt",
            storage_type="local",
            creator_id=uuid4(),
            status=ArtifactStatus.attached,
            access_level="private",
            created_at=now,
            updated_at=now,
        )

        # Old orphaned artifact with existing file (should be hard deleted)
        old_id = uuid4()
        old_date = now - timedelta(days=8)
        old = Artifact(
            id=old_id,
            title="old",
            artifact_type="file",
            mime="text/plain",
            storage_path=f"{old_id}/old.txt",
            storage_type="local",
            creator_id=uuid4(),
            status=ArtifactStatus.orphaned,
            access_level="private",
            created_at=old_date,
            updated_at=old_date,
        )

        session.add_all([missing, old])
        session.commit()

    # Create file for old orphaned artifact
    _touch(uploads_dir / f"{old_id}" / "old.txt")

    # Create disk-only orphan dir older than retention
    disk_only_id = uuid4()
    disk_only_dir = uploads_dir / str(disk_only_id)
    disk_only_dir.mkdir(parents=True, exist_ok=True)
    _touch(disk_only_dir / "x.bin")
    old_ts = time.time() - (8 * 86400)
    os.utime(disk_only_dir, (old_ts, old_ts))

    # DRY RUN: should report actions but not change DB/FS
    report = run_orphan_cleanup_once(
        7,
        dry_run=True,
        uploads_dir=uploads_dir,
        sessionmaker=test_db,
    )

    assert missing_id in report.marked_missing
    assert old_id in report.hard_deleted_orphaned
    assert str(disk_only_dir) in report.deleted_disk_only_dirs

    with test_db() as session:
        still_missing = session.get(Artifact, missing_id)
        still_old = session.get(Artifact, old_id)
        assert still_missing is not None
        assert still_missing.status == ArtifactStatus.attached
        assert still_old is not None

    assert (uploads_dir / f"{old_id}" / "old.txt").exists()
    assert disk_only_dir.exists()

    # APPLY: should perform changes
    report2 = run_orphan_cleanup_once(
        7,
        dry_run=False,
        uploads_dir=uploads_dir,
        sessionmaker=test_db,
    )

    assert missing_id in report2.marked_missing
    assert old_id in report2.hard_deleted_orphaned
    assert str(disk_only_dir) in report2.deleted_disk_only_dirs

    with test_db() as session:
        updated_missing = session.get(Artifact, missing_id)
        deleted_old = session.get(Artifact, old_id)
        assert updated_missing is not None
        assert updated_missing.status == ArtifactStatus.orphaned
        assert deleted_old is None

    assert not (uploads_dir / f"{old_id}" / "old.txt").exists()
    assert not disk_only_dir.exists()
