from fastapi import FastAPI, Path, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fair_platform.backend.data.database import init_db
from fair_platform.backend.api.routers.users import router as users_router
from fair_platform.backend.api.routers.courses import router as courses_router
from fair_platform.backend.api.routers.artifacts import router as artifacts_router
from fair_platform.backend.api.routers.assignments import router as assignments_router
from fair_platform.backend.api.routers.plugins import router as plugins_router
from fair_platform.backend.api.routers.submissions import router as submissions_router
from fair_platform.backend.api.routers.workflows import router as workflows_router
from fair_platform.backend.api.routers.workflow_runs import router as workflow_runs_router
from fair_platform.backend.api.routers.auth import router as auth_router
import importlib.resources

@asynccontextmanager
async def lifespan(_ignored: FastAPI):
    init_db()
    try:
        yield
    finally:
        # teardown?
        pass


app = FastAPI(title="Fair Platform Backend", version="0.1.0", lifespan=lifespan)

# TODO: use env variable
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(courses_router, prefix="/api/courses", tags=["courses"])
app.include_router(artifacts_router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(assignments_router, prefix="/api/assignments", tags=["assignments"])
app.include_router(plugins_router, prefix="/api/plugins", tags=["plugins"])
app.include_router(submissions_router, prefix="/api/submissions", tags=["submissions"])
app.include_router(workflows_router, prefix="/api/workflows", tags=["workflows"])
app.include_router(workflow_runs_router, prefix="/api/workflow-runs", tags=["workflow-runs"])

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    run()


def run(host: str = "127.0.0.1", port: int = 8000, headless: bool = False):
    if not headless:
        @app.get("/{full_path:path}")
        def serve(full_path: str):
            package_path = importlib.resources.files("fair_platform.frontend") / "dist"
            file_path = package_path / full_path

            if file_path.is_file():
                with importlib.resources.as_file(file_path) as file_path:
                    return FileResponse(file_path)
            elif (package_path / "index.html").is_file():
                with importlib.resources.as_file(package_path / "index.html") as index_file:
                    return FileResponse(index_file)
            return HTTPException(status_code=404, detail="Not Found")

    import uvicorn
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    main()