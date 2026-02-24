import importlib.resources
import os
import logging
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
from fair_platform.backend.api.routers.sessions import router as sessions_router
from fair_platform.backend.api.routers.version import router as version_router
from fair_platform.backend.api.routers.rubrics import router as rubrics_router
from fair_platform.backend.api.routers.enrollments import router as enrollments_router

from fair_platform.sdk import load_storage_plugins

logger = logging.getLogger(__name__)


def _is_auto_migrate_enabled() -> bool:
    raw = os.getenv("FAIR_AUTO_MIGRATE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _is_create_all_fallback_enabled() -> bool:
    raw = os.getenv("FAIR_ALLOW_CREATE_ALL", "0").strip().lower()
    return raw in {"1", "true", "yes", "on"}


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
    load_storage_plugins()
    try:
        yield
    finally:
        # teardown?
        pass


app = FastAPI(
    title="Fair Platform Backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(courses_router, prefix="/api/courses", tags=["courses"])
app.include_router(artifacts_router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(assignments_router, prefix="/api/assignments", tags=["assignments"])
app.include_router(plugins_router, prefix="/api/plugins", tags=["plugins", "workflows", "sessions"])
app.include_router(submissions_router, prefix="/api/submissions", tags=["submissions"])
app.include_router(submission_results_router, prefix="/api/submission-results")
app.include_router(workflows_router, prefix="/api/workflows", tags=["workflows", "plugins", "sessions"])
app.include_router(workflow_runs_router, prefix="/api/workflow-runs", tags=["workflow-runs", "workflows"])
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions", "workflows", "plugins"])
app.include_router(version_router, prefix="/api", tags=["version"])
app.include_router(rubrics_router, prefix="/api/rubrics", tags=["rubrics"])
app.include_router(enrollments_router, prefix="/api/enrollments", tags=["enrollments"])


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    run()


def run(
    host: str = "127.0.0.1", port: int = 8000, headless: bool = False, dev: bool = False, serve_docs: bool = False
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
        
        if serve_docs:
            docs_dir = frontend_files / "docs"
            with importlib.resources.as_file(docs_dir) as docs_path:
                app.mount("/docs", StaticFiles(directory=docs_path, html=True), name="docs")


        @app.middleware("http")
        async def spa_fallback(request, call_next):
            response = await call_next(request)
            if response.status_code == 404:
                return FileResponse(dist_path / "index.html")
            return response

    if dev:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    import uvicorn

    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
