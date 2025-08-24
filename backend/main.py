from fastapi import FastAPI
from contextlib import asynccontextmanager
from data.database import init_db
from api.routers.users import router as users_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    try:
        yield
    finally:
        # teardown?
        pass


app = FastAPI(title="Fair Platform Backend", version="0.1.0", lifespan=lifespan)

app.include_router(users_router, prefix="/api/users", tags=["users"])


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