# Fair Platform — AI Agent Instructions (updated)

High-level architecture
- Monorepo with 3 parts:
	- CLI (`cli/`): Typer app. Commands: `fair serve` (runs frontend dev server with Bun), `fair db ...` (Alembic wrapper: upgrade/downgrade/revision).
	- Backend (`backend/`): FastAPI app (`backend/main.py`) + SQLAlchemy 2.0 models in `backend/data/models/*` + Alembic migrations in `backend/alembic/`.
	- Frontend (`platform/`): Vite + React 19 + Tailwind v4, managed with Bun. HTTP via Axios (`src/lib/api.ts`) to `http://localhost:8000/api`.

Run and develop
- Backend: uvicorn serves at 8000.
	- Example: run `uvicorn backend.main:app --reload --port 8000` (requires `pip install -e backend`).
	- DB: `backend/data/database.py` uses `DATABASE_URL` (defaults to SQLite file `backend/fair.db`). Tables auto-create via `init_db()` on startup; for migrations use Alembic (see CLI below).
- Frontend: dev server via Bun/Vite.
	- Example: `cd platform && bun install && bun run dev --port 3000` or `fair serve -p 3000`.
	- CORS: backend allows `http://localhost:3000` (see `backend/main.py`), so prefer port 3000 for dev.
- DB migrations: `fair db upgrade head`, `fair db revision -m "message" --autogenerate`, `fair db downgrade -1` (runs in `backend/`).

Backend patterns you should follow
- Routers live in `backend/api/routers/*` and are mounted in `backend/main.py` with prefixes like `/api/users`, `/api/assignments`, …
	- Example: `assignments.py` shows CRUD with auth and linking via an association table (`assignment_artifacts`).
- Auth: `api/routers/auth.py` implements a mock JWT flow using OAuth2PasswordBearer with token URL `/api/auth/mock_login`. Use `get_current_user` as a dependency for protected routes.
- DB access: import `Session` via `Depends(session_dependency)` from `backend/data/database.py`. Commit on changes; `db.get(Model, id)` for lookups.
- Data shapes: Pydantic models under `backend/api/schema/*` mirror SQLAlchemy models (e.g., `AssignmentCreate/Update/Read`), with `orm_mode = True` and enums like `UserRole` from `data.models.user`.

Frontend conventions
- Tech: React 19, Vite, Tailwind v4, Radix UI primitives; utilities in `src/lib/*` (axios client, fonts, query client, utils).
- HTTP: `src/lib/api.ts` sets baseURL `http://localhost:8000/api` and injects `Authorization: Bearer <token>` from `localStorage` in a request interceptor.
- Routing/UI: React Router (v7) components under `src/app/*` and shared UI in `src/components/*` (e.g., `header.tsx`, `components/ui/*`).
- Fonts: local in `public/fonts/*` and wired via `src/lib/fonts.ts`; Tailwind config in `platform/tailwind.config.ts` and global styles in `src/globals.css`.

End-to-end flow (example)
1) Start backend: `uvicorn backend.main:app --reload --port 8000`.
2) Start frontend: `fair serve -p 3000`.
3) Register or mock-login via `/api/auth/register` or `/api/auth/mock-login`; token is stored client-side and sent by Axios.
4) Call resource endpoints like `/api/assignments` which enforce role checks using `get_current_user` and course ownership.

Adding a new resource (minimal recipe)
- Create SQLAlchemy model in `backend/data/models/<resource>.py` and import it in `backend/data/models/__init__.py` if present.
- Create Pydantic schemas in `backend/api/schema/<resource>.py`.
- Add a router in `backend/api/routers/<resource>.py` using `Session = Depends(session_dependency)` and optional `current_user = Depends(get_current_user)`; include it in `backend/main.py` with a suitable `/api/<resource>` prefix.
- Generate a migration: `fair db revision -m "add <resource>" --autogenerate` then `fair db upgrade head`.
- Frontend: call via `src/lib/api.ts` and add hooks in `src/hooks/*` or pages in `src/app/*`.

Notable constraints and tips
- Ports: axios targets 8000; keep the frontend on 3000 unless you also update CORS in `backend/main.py`.
- SQLite concurrency: `check_same_thread=False` is set for dev; for Postgres use `DATABASE_URL` (postgresql://…).
- Deletions/links: `assignments.update` replaces artifact links wholesale when `artifacts` is provided; mirror this behavior client-side.
