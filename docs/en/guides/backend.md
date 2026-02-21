---
title: Backend (Guide)
description: Overview of the Fair Platform backend architecture (FastAPI + SQLAlchemy + plugins) and how to develop it locally.
---

This page is an **English placeholder** for the Fair Platform **backend** guide. It exists to:

- Prevent 404s when navigating the **Guides** tab
- Provide a stable URL for linking and expansion
- Outline the backend’s architecture and development workflows

If you prefer Spanish, see:

- `/es/guides/backend`

---

## What is the backend?

The backend is the server-side application that:

- Exposes the **HTTP API** used by the web UI and external clients
- Manages **authentication** and authorization
- Persists the platform’s core entities (users, courses, assignments, submissions, artifacts)
- Loads and executes **plugins/extensions** (transcribers/interpreters, graders, validators, storage)
- Serves the **embedded frontend** (unless running headless)

In the repo, backend code lives under:

- `src/fair_platform/backend/`

The CLI entrypoint that orchestrates serving is under:

- `src/fair_platform/cli/`

---

## Core components (high level)

### FastAPI application
The backend is implemented with **FastAPI**. Typical responsibilities:

- Application lifespan setup (startup/shutdown tasks)
- Router registration (auth, courses, assignments, plugins, etc.)
- Dependency injection (auth, DB session, request context)
- Static file serving + SPA fallback (when serving the embedded frontend)

### Database (SQLAlchemy)
The backend uses **SQLAlchemy** for persistence.

Common expectations:

- Local development defaults to **SQLite**
- Production deployments often use **PostgreSQL** via `DATABASE_URL`

This guide will be expanded with concrete details on:

- Where engine/session lifecycle is created
- How models are organized
- How DB initialization/migrations are handled in this project

### Authentication
The platform uses **token-based authentication** (JWT).

At a high level:

- Users authenticate via auth endpoints
- Clients send the access token via:
  - `Authorization: Bearer <token>`

See:

- `/en/api-reference/authentication`

### Plugin loading and execution
FAIR is designed to be extensible. The backend:

- Discovers available plugins at startup
- Validates plugin configuration using typed settings schemas
- Orchestrates plugin execution as part of submission processing/grading workflows
- Exposes plugin inventory/configuration via API endpoints for the UI

See:

- `/en/sdk/overview`

---

## Running the backend locally

### Backend dev mode (API on a separate port)
This is useful when you run the frontend dev server separately (Vite/Bun) or when you’re working on API endpoints, DB, auth, or plugins.

Example:

```/dev/null/backend-dev.sh#L1-2
uv run fair serve --dev --port 8000
```

Notes:

- Dev mode typically enables CORS to support the frontend dev server.
- The frontend (dev server) commonly runs on `http://localhost:3000`, while the backend API runs on `http://localhost:8000`.

### Headless mode (API only)
Use this when you don’t want the backend to serve the embedded frontend.

```/dev/null/backend-headless.sh#L1-1
uv run fair serve --headless --port 8000
```

### Full platform mode (embedded frontend)
This mode serves the built frontend assets embedded into the Python package.

Typical flow:

1. Build frontend assets and copy them into the Python package
2. Start the server
3. Visit `http://localhost:3000`

```/dev/null/build-and-serve.sh#L1-3
uv sync
./build.sh
uv run fair serve --port 3000
```

---

## API conventions (placeholder)

The API generally follows these conventions:

- JSON request/response for most endpoints
- `multipart/form-data` for upload flows (submissions/artifacts)
- JWT-based auth via the `Authorization` header

See:

- `/en/api-reference/overview`
- `/en/api-reference/endpoints`

---

## Development tips (backend)

This section will be expanded, but good defaults:

- Prefer small, composable routers and dependencies
- Keep endpoint input/output schemas explicit and versionable
- Add structured logging for workflows (submissions → artifacts → grading)
- Treat plugin inputs/outputs as contract boundaries; validate aggressively
- Make “reproducibility” a first-class concern (store artifacts, record settings, preserve provenance)

---

## Roadmap for this guide

Planned additions:

- Repository map: where the FastAPI app is defined, where routers live
- Database lifecycle: engine/session pattern used in this codebase
- Auth flow: token issuance, refresh, role/permission checks
- Static serving: embedded frontend routing and SPA fallback behavior
- Plugin loading internals: discovery, registration, settings schema generation
- Debugging playbook: common errors and where to look

---

## Related pages

- Installation (developers): `/en/guides/installation`
- Development workflow: `/en/guides/development-workflow`
- Frontend guide: `/en/guides/frontend`
- Plugins guide: `/en/guides/plugins`
- SDK overview: `/en/sdk/overview`
- API overview: `/en/api-reference/overview`
