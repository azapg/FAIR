---
title: Development workflow
description: Recommended workflows for developing Fair Platform (backend, frontend, plugins) locally.
---

This page is an **English placeholder** to prevent 404s and to document the recommended workflows for developing Fair Platform locally.

As the project evolves, this guide will be expanded with concrete commands, environment variables, and troubleshooting steps.

---

## Who this guide is for

Use this guide if you are:

- Developing the **backend** (FastAPI + database + plugin loading)
- Developing the **frontend** (Vite + React + TypeScript)
- Developing **SDK plugins** (graders, transcribers/interpreters, validators, storage)
- Working on **docs** and releases

If you only want to run Fair Platform as a user, see:

- `/en/getting-started/installation`

---

## Common workflows

### 1) Run the full platform (embedded frontend)

This is the closest to “production-style” behavior: the backend serves the compiled frontend assets.

Typical loop:

1. Build the frontend assets and copy them into the Python package
2. Start the server
3. Refresh the browser to see changes (rebuild required for frontend changes)

Commands (example):

```/dev/null/dev-workflow.txt#L1-6
uv sync
./build.sh
uv run fair serve --port 3000
```

Notes:

- If you change frontend code, you generally need to re-run `./build.sh`.
- If you change backend code, restart `fair serve`.

---

### 2) Frontend dev server + backend dev API (recommended for UI work)

This workflow gives you fast HMR for the UI, while calling the backend API via proxy.

Typical loop:

- Run backend in dev mode (enables CORS for frontend dev)
- Run frontend dev server (Vite)
- Iterate quickly with hot reload

Commands (example):

```/dev/null/dev-workflow.txt#L1-9
# Terminal 1 (backend)
uv run fair serve --dev --port 8000

# Terminal 2 (frontend)
cd frontend-dev
bun install
bun run dev
```

Notes:

- Frontend typically runs on `http://localhost:3000`
- Backend API typically runs on `http://localhost:8000`

---

### 3) Backend-only (API/headless)

Use this if you’re building API endpoints, auth, DB, or plugin loading and don’t need the web UI.

```/dev/null/dev-workflow.txt#L1-2
uv run fair serve --headless --port 8000
```

---

## Project structure (high level)

- `src/fair_platform/cli/`: Typer CLI entrypoints (e.g. `fair serve`)
- `src/fair_platform/backend/`: FastAPI app, routers, database, auth, plugin loading
- `frontend-dev/`: React/Vite frontend (Bun)
- `src/fair_platform/frontend/dist/`: Embedded static frontend assets (build output copy target)
- `src/fair_platform/sdk/`: Plugin base classes and schemas

---

## Recommended development habits

- Keep API changes backward-compatible when possible.
- When adding a feature, update:
  - API routes and schemas (backend)
  - UI behavior (frontend)
  - Docs (this site)
- Prefer small PRs with clear scope.

---

## Troubleshooting (placeholder)

This will be expanded, but common issues include:

- “Port already in use”: run on a different port.
- Frontend changes not appearing: rebuild embedded assets with `./build.sh`.
- CORS errors in frontend dev: ensure backend started with `--dev`.

---

## Next pages

- `/en/guides/frontend`
- `/en/guides/backend`
- `/en/guides/plugins`
- `/en/guides/releases`
