from fastapi import FastAPI
from contextlib import asynccontextmanager
from data.database import init_db
from api.routers.users import router as users_router
from api.routers.courses import router as courses_router
from api.routers.artifacts import router as artifacts_router
from api.routers.assignments import router as assignments_router
from api.routers.plugins import router as plugins_router
from api.routers.submissions import router as submissions_router
from api.routers.workflows import router as workflows_router
from api.routers.workflow_runs import router as workflow_runs_router

@asynccontextmanager
async def lifespan(_ignored: FastAPI):
    init_db()
    try:
        yield
    finally:
        # teardown?
        pass


app = FastAPI(title="Fair Platform Backend", version="0.1.0", lifespan=lifespan)

app.include_router(users_router, prefix="/api/users", tags=["users"])
app.include_router(courses_router, prefix="/api/courses", tags=["courses"])
app.include_router(artifacts_router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(assignments_router, prefix="/api/assignments", tags=["assignments"])
app.include_router(plugins_router, prefix="/api/plugins", tags=["plugins"])
app.include_router(submissions_router, prefix="/api/submissions", tags=["submissions"])
app.include_router(workflows_router, prefix="/api/workflows", tags=["workflows"])
app.include_router(workflow_runs_router, prefix="/api/workflow-runs", tags=["workflow-runs"])

@app.get("/")
def read_root():
    return {"message": "Hello from backend!"}


@app.get("/health")
def health():
    return {"status": "ok"}


def main():
    # Local dev runner
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    main()