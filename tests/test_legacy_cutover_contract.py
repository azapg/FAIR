"""Executable checklist for removing the pre-1.0 execution stack.

The inventory tests prevent a removed surface from being added again.
Historical Alembic revisions are deliberately not part of the source-removal
inventory.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from fair_platform.backend.main import app


REPO_ROOT = Path(__file__).parents[1]
BACKEND_ROOT = REPO_ROOT / "src/fair_platform/backend"


@dataclass(frozen=True)
class CutoverStage:
    number: int
    name: str
    depends_on: tuple[str, ...]
    routes: tuple[str, ...] = ()
    files: tuple[str, ...] = ()


CUTOVER_STAGES = (
    CutoverStage(
        1,
        "workflow-run public adapter",
        (
            "Execution create/read/event/stream APIs cover all callers",
            "submission code no longer imports WorkflowRun schemas or services",
        ),
        routes=(
            "/api/workflow-runs/",
            "/api/workflow-runs/{workflow_run_id}",
            "/api/workflow-runs/{workflow_run_id}/stream",
        ),
        files=(
            "api/routers/workflow_runs.py",
            "api/schema/workflow_run.py",
        ),
    ),
    CutoverStage(
        5,
        "unversioned Extension and Artifact adapters",
        (
            "stages 1 through 4 are complete",
            "all callers use canonical /api/v1 resources",
        ),
        files=(
            "api/routers/legacy_artifacts.py",
            "api/schema/legacy_artifact.py",
            "data/models/legacy_artifact.py",
        ),
    ),
    CutoverStage(
        2,
        "workflow definitions and runner",
        (
            "stage 1 is complete",
            "Flow and FlowVersion APIs own ordered definitions",
            "Execution dispatch no longer calls WorkflowRunner",
        ),
        routes=(
            "/api/workflows/",
            "/api/workflows/{workflow_id}",
        ),
        files=(
            "api/routers/workflows.py",
            "api/schema/workflow.py",
            "data/models/workflow.py",
            "data/models/workflow_run.py",
            "services/workflow_runner.py",
        ),
    ),
    CutoverStage(
        3,
        "public Job transport",
        (
            "stages 1 and 2 are complete",
            "execution outbox dispatcher is the only work-delivery entrypoint",
            "extensions acknowledge commands and append Execution events",
        ),
        routes=(
            "/api/jobs/",
            "/api/jobs/{job_id}",
            "/api/jobs/{job_id}/stream",
            "/api/jobs/{job_id}/updates",
        ),
        files=(
            "api/dependencies/job_queue.py",
            "api/routers/jobs.py",
            "api/schema/job.py",
            "services/job_dispatcher.py",
            "services/job_queue.py",
        ),
    ),
    CutoverStage(
        4,
        "Plugin compatibility resources",
        (
            "stages 1 through 3 are complete",
            "Extension installation/capability APIs replace plugin discovery",
            "frontend and assignments persist extension/capability identities",
        ),
        routes=(
            "/api/plugins/",
            "/api/plugins/{plugin_id}",
        ),
        files=(
            "api/routers/plugins.py",
            "api/schema/plugin.py",
        ),
    ),
)

DECLARED_LEGACY_ROUTES = {
    route for stage in CUTOVER_STAGES for route in stage.routes
}
DECLARED_LEGACY_FILES = {
    file for stage in CUTOVER_STAGES for file in stage.files
}
LEGACY_ROUTE_PREFIXES = (
    "/api/workflows",
    "/api/workflow-runs",
    "/api/jobs",
    "/api/plugins",
    "/api/extensions",
    "/api/artifacts",
)


def _openapi_legacy_routes() -> set[str]:
    return {
        path
        for path in app.openapi()["paths"]
        if path.startswith(LEGACY_ROUTE_PREFIXES)
    }


def _discover_named_legacy_files() -> set[str]:
    candidates = set()
    for path in BACKEND_ROOT.rglob("*.py"):
        relative = path.relative_to(BACKEND_ROOT).as_posix()
        if relative.startswith("alembic/"):
            continue
        name = path.stem
        if "workflow" in name or name in {
            "job",
            "jobs",
            "job_queue",
            "job_dispatcher",
            "plugin",
            "plugins",
        }:
            candidates.add(relative)
    return candidates


def test_openapi_legacy_inventory_has_no_unlisted_surfaces() -> None:
    unlisted = _openapi_legacy_routes() - DECLARED_LEGACY_ROUTES
    assert not unlisted, f"Add unlisted legacy routes to a cutover stage: {sorted(unlisted)}"


def test_source_legacy_inventory_has_no_unlisted_files() -> None:
    unlisted = _discover_named_legacy_files() - DECLARED_LEGACY_FILES
    assert not unlisted, f"Add unlisted legacy files to a cutover stage: {sorted(unlisted)}"


@pytest.mark.parametrize("stage", CUTOVER_STAGES, ids=lambda stage: f"stage-{stage.number}-{stage.name}")
def test_legacy_cutover_stage_is_complete(stage: CutoverStage) -> None:
    remaining_routes = sorted(set(stage.routes) & _openapi_legacy_routes())
    remaining_files = sorted(
        file for file in stage.files if (BACKEND_ROOT / file).is_file()
    )
    assert not remaining_routes and not remaining_files, (
        f"Cutover stage {stage.number} ({stage.name}) regressed. "
        f"Dependencies: {'; '.join(stage.depends_on)}. "
        f"Remaining routes: {remaining_routes}. Remaining files: {remaining_files}."
    )


def test_legacy_cutover_is_complete() -> None:
    remaining_routes = sorted(_openapi_legacy_routes())
    remaining_files = sorted(
        file for file in DECLARED_LEGACY_FILES if (BACKEND_ROOT / file).is_file()
    )
    assert not remaining_routes and not remaining_files, (
        "Legacy cutover regressed. "
        f"Remaining routes: {remaining_routes}. Remaining files: {remaining_files}."
    )
