from __future__ import annotations

import asyncio
import logging
import shutil
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from fair_platform.backend.data.database import get_session
from fair_platform.backend.data.models.artifact import Artifact, ArtifactStatus
from fair_platform.backend.data.storage import storage
from fair_platform.backend.services.artifact_manager import ArtifactManager

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CleanupReport:
    retention_days: int
    dry_run: bool
    marked_missing: list[UUID] = field(default_factory=list)
    hard_deleted_orphaned: list[UUID] = field(default_factory=list)
    deleted_disk_only_dirs: list[str] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "marked_missing": len(self.marked_missing),
            "hard_deleted_orphaned": len(self.hard_deleted_orphaned),
            "deleted_disk_only_dirs": len(self.deleted_disk_only_dirs),
        }


@contextmanager
def _session_from_sessionmaker(sessionmaker) -> Iterator[Session]:
    session: Session = sessionmaker()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _iter_upload_uuid_dirs(uploads_dir: Path) -> Iterable[Path]:
    if not uploads_dir.exists():
        return []
    for child in uploads_dir.iterdir():
        if child.is_dir():
            yield child


def run_orphan_cleanup_once(
    retention_days: int,
    *,
    dry_run: bool = False,
    uploads_dir: Optional[Path] = None,
    sessionmaker=None,
) -> CleanupReport:
    """Run a single orphan cleanup pass.

    This function is the shared core used by:
    - the periodic background job (in-process)
    - the debugging/tooling script

    It covers:
    1) DB rows pointing to missing files -> mark as orphaned
    2) orphaned rows older than retention -> hard delete from FS + remove from DB
    3) disk-only UUID dirs under uploads/ with no DB row -> delete after retention

    Args:
        retention_days: Delete threshold in days (N).
        dry_run: If True, only report actions; do not mutate DB or filesystem.
        uploads_dir: Optional override for uploads directory.
        sessionmaker: Optional SQLAlchemy sessionmaker for tests.

    Returns:
        CleanupReport
    """

    if retention_days < 0:
        raise ValueError("retention_days must be >= 0")

    effective_uploads_dir = Path(uploads_dir) if uploads_dir is not None else storage.uploads_dir

    report = CleanupReport(retention_days=retention_days, dry_run=dry_run)

    session_ctx = _session_from_sessionmaker(sessionmaker) if sessionmaker is not None else get_session()

    # Keep cutoff logic consistent with ArtifactManager.cleanup_orphaned()
    now = datetime.now()
    cutoff_dt = now - timedelta(days=retention_days)
    cutoff_ts = cutoff_dt.timestamp()

    # Storage backend override so ArtifactManager deletes from the same uploads_dir we scan.
    storage_backend = None
    if uploads_dir is not None:
        class _StorageBackend:
            def __init__(self, uploads_dir: Path):
                self.uploads_dir = uploads_dir

        storage_backend = _StorageBackend(effective_uploads_dir)

    with session_ctx as session:
        # Build set of existing artifact IDs for FS->DB scan.
        existing_ids = {row[0] for row in session.query(Artifact.id).all()}

        # Phase 1: DB -> FS consistency (missing file => orphaned)
        local_artifacts = (
            session.query(Artifact)
            .filter(Artifact.storage_type == "local")
            .all()
        )

        for artifact in local_artifacts:
            file_path = effective_uploads_dir / artifact.storage_path
            if file_path.exists():
                continue

            # Only transition active artifacts to orphaned.
            if artifact.status in (ArtifactStatus.archived, ArtifactStatus.orphaned):
                continue

            report.marked_missing.append(artifact.id)
            if not dry_run:
                artifact.status = ArtifactStatus.orphaned
                artifact.updated_at = now
                session.add(artifact)

        # Phase 2: hard delete orphaned older than retention
        orphaned_to_delete = (
            session.query(Artifact)
            .filter(
                Artifact.status == ArtifactStatus.orphaned,
                Artifact.updated_at < cutoff_dt,
            )
            .all()
        )
        report.hard_deleted_orphaned.extend(a.id for a in orphaned_to_delete)

        if not dry_run and orphaned_to_delete:
            manager = ArtifactManager(session, storage_backend=storage_backend)
            manager.cleanup_orphaned(older_than_days=retention_days, hard_delete=True)

        # Phase 3: FS -> DB consistency (disk-only UUID directories)
        for uuid_dir in _iter_upload_uuid_dirs(effective_uploads_dir):
            try:
                dir_uuid = UUID(uuid_dir.name)
            except Exception:
                continue

            if dir_uuid in existing_ids:
                continue

            try:
                mtime = uuid_dir.stat().st_mtime
            except FileNotFoundError:
                continue

            if mtime >= cutoff_ts:
                continue

            report.deleted_disk_only_dirs.append(str(uuid_dir))
            if not dry_run:
                shutil.rmtree(uuid_dir, ignore_errors=True)

    return report


async def orphan_cleanup_loop(
    stop_event: asyncio.Event,
    *,
    interval_seconds: int,
    retention_days: int,
    dry_run: bool = False,
) -> None:
    """Periodic orphan cleanup loop.

    Runs immediately once, then every interval_seconds until stop_event is set.
    """

    if interval_seconds <= 0:
        raise ValueError("interval_seconds must be > 0")

    while not stop_event.is_set():
        try:
            report = run_orphan_cleanup_once(retention_days, dry_run=dry_run)
            logger.info(
                "Orphan cleanup run finished (dry_run=%s): %s",
                dry_run,
                report.counts,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Orphan cleanup run failed")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            continue
