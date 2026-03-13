import importlib.resources
import os
import logging
import asyncio
import sys
from fastapi import FastAPI
from contextlib import asynccontextmanager

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from fair_platform.backend.data.database import init_db
from fair_platform.backend.data.migrations import run_migrations_to_head
from fair_platform.backend.api.routers.users import router as users_router
from fair_platform.backend.api.routers.courses import router as courses_router
from fair_platform.backend.api.routers.artifacts import router as artifacts_router
from fair_platform.backend.api.routers.assignments import router as assignments_router
from fair_platform.backend.api.routers.plugins import router as plugins_router
from fair_platform.backend.api.routers.submissions import router as submissions_router
from fair_platform.backend.api.routers.submission_results import (
    router as submission_results_router,
)
from fair_platform.backend.api.routers.workflows import router as workflows_router
from fair_platform.backend.api.routers.workflow_runs import router as workflow_runs_router
from fair_platform.backend.api.routers.auth import router as auth_router
from fair_platform.backend.api.routers.version import router as version_router
from fair_platform.backend.api.routers.rubrics import router as rubrics_router
from fair_platform.backend.api.routers.enrollments import router as enrollments_router
from fair_platform.backend.api.routers.jobs import router as jobs_router
from fair_platform.backend.api.routers.extensions import router as extensions_router
from fair_platform.backend.api.routers.system import router as system_router
from fair_platform.backend.services.extension_registry import LocalExtensionRegistry
from fair_platform.backend.services.job_dispatcher import JobDispatcher
from fair_platform.backend.services.job_queue import create_job_queue
from fair_platform.backend.services.workflow_runner import (
    WorkflowRunEventBroker,
    WorkflowRunner,
)
from fair_platform.backend.data.database import SessionLocal
from fair_platform.backend.data.models import ExtensionClient
from fair_platform.backend.services.extension_auth import hash_extension_secret

logger = logging.getLogger(__name__)

CORE_EXTENSION_ID = "fair.core"
CORE_EXTENSION_SECRET = "fair-core-dev-secret"


def _is_auto_migrate_enabled() -> bool:
    raw = os.getenv("FAIR_AUTO_MIGRATE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _is_create_all_fallback_enabled() -> bool:
    raw = os.getenv("FAIR_ALLOW_CREATE_ALL", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _configured_cors_origins() -> list[str]:
    raw = os.getenv("FAIR_CORS_ORIGINS", "").strip()
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    # Sensible local defaults for frontend dev servers.
    return [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def _is_job_dispatcher_enabled() -> bool:
    raw = os.getenv("FAIR_ENABLE_JOB_DISPATCHER", "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _is_core_extension_enabled() -> bool:
    if os.getenv("PYTEST_CURRENT_TEST"):
        return False
    raw = os.getenv("FAIR_ENABLE_CORE_EXTENSION", "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _core_extension_id() -> str:
    return os.getenv("FAIR_CORE_EXTENSION_ID", CORE_EXTENSION_ID).strip() or CORE_EXTENSION_ID


def _core_extension_secret() -> str:
    return os.getenv("FAIR_CORE_EXTENSION_SECRET", CORE_EXTENSION_SECRET).strip() or CORE_EXTENSION_SECRET


def _core_extension_port() -> str:
    return os.getenv("FAIR_CORE_EXTENSION_PORT", "8001").strip() or "8001"


def _ensure_core_extension_client() -> None:
    from datetime import datetime, timezone

    extension_id = _core_extension_id()
    extension_secret = _core_extension_secret()
    now = datetime.now(timezone.utc)
    session = SessionLocal()
    try:
        row = session.get(ExtensionClient, extension_id)
        scopes = ["extensions:connect", "jobs:read", "jobs:write"]
        if row is None:
            row = ExtensionClient(
                extension_id=extension_id,
                secret_hash=hash_extension_secret(extension_secret),
                scopes=scopes,
                enabled=True,
                created_at=now,
                updated_at=now,
            )
        else:
            row.secret_hash = hash_extension_secret(extension_secret)
            row.scopes = scopes
            row.enabled = True
            row.updated_at = now
        session.add(row)
        session.commit()
    finally:
        session.close()


async def _start_core_extension() -> asyncio.subprocess.Process:
    env = dict(os.environ)
    env.setdefault("FAIR_CORE_EXTENSION_ID", _core_extension_id())
    env.setdefault("FAIR_CORE_EXTENSION_SECRET", _core_extension_secret())
    env.setdefault("FAIR_CORE_EXTENSION_PORT", _core_extension_port())
    env.setdefault("FAIR_CORE_PLATFORM_URL", os.getenv("FAIR_CORE_PLATFORM_URL", "http://127.0.0.1:8000"))
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "uvicorn",
        "fair_platform.extensions.core.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        env["FAIR_CORE_EXTENSION_PORT"],
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
        env=env,
    )
    return process


@asynccontextmanager
async def lifespan(_ignored: FastAPI):
    if _is_auto_migrate_enabled():
        run_migrations_to_head()
    elif _is_create_all_fallback_enabled():
        # Explicit opt-in fallback for local/test-only environments.
        init_db()
    else:
        logger.warning(
            "FAIR_AUTO_MIGRATE is disabled and FAIR_ALLOW_CREATE_ALL is not enabled. "
            "Starting without schema migration/bootstrap; runtime DB failures are likely. "
            "Set FAIR_AUTO_MIGRATE=1 (recommended) or FAIR_ALLOW_CREATE_ALL=1 for local-only bootstrap."
        )
    app.state.job_queue = await create_job_queue()
    app.state.extension_registry = LocalExtensionRegistry()
    app.state.workflow_run_event_broker = WorkflowRunEventBroker()
    app.state.job_dispatcher = JobDispatcher(
        queue=app.state.job_queue,
        registry=app.state.extension_registry,
    )
    app.state.workflow_runner = WorkflowRunner(
        job_queue=app.state.job_queue,
        event_broker=app.state.workflow_run_event_broker,
    )
    app.state.core_extension_process = None
    if _is_core_extension_enabled():
        _ensure_core_extension_client()
        app.state.core_extension_process = await _start_core_extension()
    if _is_job_dispatcher_enabled():
        await app.state.job_dispatcher.start()
    try:
        yield
    finally:
        core_process = getattr(app.state, "core_extension_process", None)
        if core_process is not None and core_process.returncode is None:
            core_process.terminate()
            try:
                await asyncio.wait_for(core_process.wait(), timeout=10.0)
            except TimeoutError:
                core_process.kill()
                await core_process.wait()
        dispatcher = getattr(app.state, "job_dispatcher", None)
        if dispatcher is not None:
            await dispatcher.stop()
        queue = getattr(app.state, "job_queue", None)
        if queue is not None:
            await queue.close()


app = FastAPI(
    title="Fair Platform Backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_configured_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(courses_router, prefix="/api/courses", tags=["courses"])
app.include_router(artifacts_router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(assignments_router, prefix="/api/assignments", tags=["assignments"])
app.include_router(plugins_router, prefix="/api/plugins", tags=["plugins", "workflows"])
app.include_router(submissions_router, prefix="/api/submissions", tags=["submissions"])
app.include_router(submission_results_router, prefix="/api/submission-results")
app.include_router(workflows_router, prefix="/api/workflows", tags=["workflows", "plugins"])
app.include_router(workflow_runs_router, prefix="/api/workflow-runs", tags=["workflow-runs", "workflows"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(version_router, prefix="/api", tags=["version"])
app.include_router(rubrics_router, prefix="/api/rubrics", tags=["rubrics"])
app.include_router(enrollments_router, prefix="/api/enrollments", tags=["enrollments"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["jobs"])
app.include_router(extensions_router, prefix="/api/extensions", tags=["extensions"])
app.include_router(system_router, prefix="/api/v1/system", tags=["system"])


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    run()


def run(
    host: str = "127.0.0.1", port: int = 8000, headless: bool = False, dev: bool = False
):
    if not headless:
        frontend_files = importlib.resources.files("fair_platform.frontend")
        dist_dir = frontend_files / "dist"

        with importlib.resources.as_file(dist_dir) as dist_path:
            app.mount(
                "/assets", StaticFiles(directory=dist_path / "assets"), name="assets"
            )
            app.mount(
                "/fonts", StaticFiles(directory=dist_path / "fonts"), name="fonts"
            )
            app.mount("/data", StaticFiles(directory=dist_path / "data"), name="data")

        @app.get("/favicon.svg")
        async def favicon():
            return FileResponse(dist_path / "favicon.svg", media_type="image/svg+xml")

        @app.middleware("http")
        async def spa_fallback(request, call_next):
            response = await call_next(request)
            if response.status_code == 404:
                return FileResponse(dist_path / "index.html")
            return response

    import uvicorn

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
