import importlib.resources
from fastapi import FastAPI
from contextlib import asynccontextmanager

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.cors import CORSMiddleware

from fair_platform.backend.data.database import init_db
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
from fair_platform.backend.api.routers.auth import router as auth_router
from fair_platform.backend.api.routers.sessions import router as sessions_router
from fair_platform.backend.api.routers.version import router as version_router

from fair_platform.sdk import load_storage_plugins


@asynccontextmanager
async def lifespan(_ignored: FastAPI):
    init_db()
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
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(sessions_router, prefix="/api/sessions", tags=["sessions", "workflows", "plugins"])
app.include_router(version_router, prefix="/api", tags=["version"])


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
