FAIR (or _The Fair Platform_) is an open-source platform that makes it easy to experiment with automatic grading systems using AI. It provides a flexible and extensible environment for building, testing, and comparing grading approaches, from interpreters and rubrics to agent-based systems and research datasets.

The goal is to support researchers, educators, and students who want to explore how AI can improve assessment, reduce manual grading workload, and enable reproducible experiments in educational technology.

Fair Grade is an open-source ecosystem designed to allow researchers, professors, students, and policymakers integrate AI safely into the education system. Our Platform serves professors as a new AI-first Learning Management System (LMS) where they can manage their courses and assignments using cutting edge AI tools based on the latest research in the field.

The platform is part of the Fair Grade Project, a research initiative that aims to explore the impact of AI on education and develop tools to ensure that AI is used in a way that is fair and equitable for all students. In these early stages of development, we are focused on building a robust and user-friendly LMS with AI graders and feedback tools, a core pillar of the Fair Grade vision.

# Fair Platform - AI Agent Instructions

## Project Architecture

Five co-located components sharing one repository:

- **CLI** (`src/fair_platform/cli/`): Typer-based entry point. `fair dev` for development (launches backend + bun dev server), `fair serve` for production. Headless mode via `--headless`.
- **Backend** (`src/fair_platform/backend/`): FastAPI server — SQLAlchemy models, Alembic migrations, API routers, and background services (dispatcher, job queue).
- **Frontend** (`frontend-dev/`): Vite + React 19 SPA. Built to `frontend-dev/dist/`, then `build.sh` copies it to `src/fair_platform/frontend/dist/` for single-binary embedding.
- **Extension SDK** (`src/fair_platform/extension_sdk/`): The current external extension system. Extensions are standalone HTTP services that register with the platform and receive jobs via webhooks.

**Key architectural decision**: Extensions communicate asynchronously — the platform creates a Job, returns `202` immediately, a background Dispatcher forwards the job to the extension's webhook URL, and the client subscribes via SSE (`/api/jobs/{id}/stream`) for results.

## Build & Run

```bash
# Full build (installs deps, builds frontend, copies dist, packages)
./build.sh

# Development — single terminal starts both backend + frontend dev server:
fair dev                              # backend on :8000, frontend (bun) on :3000
fair dev --no-frontend                # backend only (no bun dev server)

# Production — serves embedded built frontend:
fair serve                            # default port 3000
fair serve --port 8080 --headless     # API only, no static files

# Run tests
uv run pytest                         # all tests
uv run pytest tests/test_auth_integration.py  # single file
```

**`build.sh`** does: `uv sync` → `bun install` → `bun run build` → copy `frontend-dev/dist/` → `src/fair_platform/frontend/dist/` → `uv build`.

## Database & Migrations

- **Primary production DB**: PostgreSQL (target v18). SQLite for local dev/tests.
- Set `DATABASE_URL=postgresql+psycopg://user:pass@host/db`. `env.py` normalizes `postgres://` and relative SQLite paths automatically.
- Schema changes **must** go through Alembic migrations:
  ```bash
  alembic revision --autogenerate -m "describe change"
  alembic upgrade head
  ```
- `FAIR_AUTO_MIGRATE=0` disables startup auto-migrate. `FAIR_ALLOW_CREATE_ALL=1` falls back to `create_all` (test/dev only).

## Extension System (Current Architecture)

Extensions are separate processes using `FairExtension` from `extension_sdk`:

```python
from fair_platform.extension_sdk import FairExtension
ext = FairExtension("my-ext", platform_url, extension_secret)
# Register an action handler
@ext.action("grade")
async def grade(ctx: JobContext, params: GradeParams): ...
```

The platform uses a **job queue abstraction** — `asyncio.Queue` locally (zero-config) and Redis in production. The Dispatcher is **enabled by default** (`FAIR_ENABLE_JOB_DISPATCHER=0` to disable). The extension registry is currently **in-memory** (not shared across workers). See `api-communications.md` for the full design.

## Testing Patterns

Tests use `pytest` with a per-test SQLite temp database via the `test_db` fixture in `tests/conftest.py`. It overrides `session_dependency` on the FastAPI app:

```python
def test_something(test_db, client):  # client fixture uses test_db
    ...
```

**Important**: `tests/TODO.md` documents disabled/removed tests that are AI-generated stubs. Do not add new AI-generated tests that pass trivially — write tests against actual endpoint behavior.

Run with `uv run pytest --tb=short`.

## Backend Conventions

- Routers live in `src/fair_platform/backend/api/routers/` (one file per resource: `jobs.py`, `extensions.py`, `submissions.py`, etc.).
- Services layer in `src/fair_platform/backend/services/` (e.g., `job_dispatcher.py`, `extension_registry.py`, `submission_manager.py`).
- JSON fields use SQLAlchemy `JSON` type with PostgreSQL JSONB variant — do not use `Text` for structured data.
- CORS origins are configured via `FAIR_CORS_ORIGINS` env var (automatically set by `fair dev`).

## Frontend Conventions

- **File naming**: All files and directories use lowercase kebab-case (e.g., `submission-sheet.tsx`, `data-table/`, `use-submissions.ts`).
- **Component library**: Always use shadcn/ui first. If a needed component doesn't exist in `frontend-dev/src/components/ui/`, install it via the shadcn CLI — don't build it from scratch.
- **Tables**: Use the project's `DataTable` compound component (`frontend-dev/src/components/data-table/`) for all tabular data. See `submissions-table.tsx` for the full pattern with columns, tabs, search, pagination, and empty states.
- **Reference page**: The submission page (`frontend-dev/src/app/assignment/components/submissions/`) is the most complete example of project patterns — badges, inline editing, markdown rendering, file artifacts, timeline, side sheet detail panels.
- **API calls**: Axios instance in `frontend-dev/src/lib/api.ts` with auth interceptors; uses `/api` in prod, `http://localhost:8000/api` in dev.
- **Fonts**: `font-serif` = Remark, `font-sans` = Host Grotesk, `font-mono` = system mono.
- **State**: Zustand for client state; TanStack Query v5 for server state with key factories.

## Key Files

| File | Purpose |
|------|---------|
| `src/fair_platform/cli/main.py` | CLI entry + backend orchestration |
| `src/fair_platform/backend/main.py` | FastAPI app, lifespan, static serving |
| `src/fair_platform/backend/services/job_dispatcher.py` | Dispatcher loop |
| `src/fair_platform/extension_sdk/extension.py` | `FairExtension` base class |
| `api-communications.md` | Full async job/extension architecture spec |
| `tests/conftest.py` | Shared test fixtures |
| `tests/TODO.md` | Disabled/broken test inventory |
