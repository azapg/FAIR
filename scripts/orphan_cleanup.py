from __future__ import annotations

import argparse
from pathlib import Path

from fair_platform.backend.jobs.orphan_cleanup import run_orphan_cleanup_once


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Debug tool: run orphan cleanup exactly like the background job. "
            "Defaults to dry-run; use --apply to perform deletions."
        )
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="Apply changes (delete files/rows). Without this, runs in dry-run mode.",
    )
    p.add_argument(
        "--retention-days",
        type=int,
        default=7,
        help="Hard-delete orphaned items older than N days (default: 7).",
    )
    p.add_argument(
        "--uploads-dir",
        type=Path,
        default=None,
        help="Override uploads directory (default: platform storage uploads dir).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-item details.",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    dry_run = not args.apply
    report = run_orphan_cleanup_once(
        args.retention_days,
        dry_run=dry_run,
        uploads_dir=args.uploads_dir,
    )

    mode = "DRY RUN" if dry_run else "APPLY"
    print(f"[{mode}] retention_days={report.retention_days}")
    print("summary:")
    for k, v in report.counts.items():
        print(f"  - {k}: {v}")

    if args.verbose:
        if report.marked_missing:
            print("\nwould_mark_missing_as_orphaned:")
            for artifact_id in report.marked_missing:
                print(f"  - {artifact_id}")
        if report.hard_deleted_orphaned:
            print("\nwould_hard_delete_orphaned:")
            for artifact_id in report.hard_deleted_orphaned:
                print(f"  - {artifact_id}")
        if report.deleted_disk_only_dirs:
            print("\nwould_delete_disk_only_dirs:")
            for p in report.deleted_disk_only_dirs:
                print(f"  - {p}")


if __name__ == "__main__":
    main()
