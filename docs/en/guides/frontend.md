---
title: Frontend
description: How the Fair Platform frontend is structured, how it talks to the backend API, and how to develop it locally.
---

This page documents the **Fair Platform frontend**: where it lives, how to run it in development, and how it integrates with the backend.

> Status: This guide is intentionally lightweight, but it is **not** an empty placeholder. It covers the core workflow and conventions used in this repo.

---

## Where the frontend lives

The frontend source code is in:

- `frontend-dev/` (Vite + React + TypeScript)

When built for production-style runs, its static assets are copied into:

- `src/fair_platform/frontend/dist/`

That second directory is what the FastAPI backend serves when you run the full platform (non-headless) via the CLI.

---

## Two ways to run the frontend

### 1) Recommended for UI work: Vite dev server (fast refresh)

This is the best workflow while actively editing frontend code:

1. Start the backend in dev mode (API)
2. Start the frontend dev server

Backend (Terminal 1):

```/dev/null/backend-dev.sh#L1-1
uv run fair serve --dev --port 8000
```

Frontend (Terminal 2):

```/dev/null/frontend-dev.sh#L1-3
cd frontend-dev
bun install
bun run dev
```

Open:

- `http://localhost:3000`

In this workflow, the frontend will call the backend API through a dev/proxy setup (commonly to `http://localhost:8000`).

### 2) Production-style: embedded static frontend (requires rebuild)

Use this when you want to validate the single-binary / embedded-frontend behavior:

1. Build the frontend
2. Copy the build output into the Python package
3. Run the server

```/dev/null/build-and-serve.sh#L1-3
uv sync
./build.sh
uv run fair serve --port 3000
```

Open:

- `http://localhost:3000`

Notes:

- If you change frontend code, you generally must re-run `./build.sh` to see changes.
- If you change backend code, restart the server.

---

## How the frontend talks to the backend

### API base URL

The frontend uses an API prefix that differs between environments:

- Production-style: API is on the same origin, usually under `/api`
- Development: API may be `http://localhost:8000/api`

This is typically handled by an Axios wrapper module, plus environment-based logic in Vite.

### Authentication

FAIR uses token-based authentication (JWT). The frontend usually stores tokens in the browser and attaches them to API calls automatically.

Practical implications for frontend work:

- If you’re seeing `401` responses, verify you’re logged in and tokens exist.
- If you change auth behavior on the backend, you’ll likely need to update:
  - auth routes/flows
  - token storage and interceptors
  - error handling (logout on `401`, etc.)

---

## Project conventions (frontend)

### State management

Fair Platform generally uses two kinds of state:

- **Server state**: fetched from the backend API (use TanStack Query patterns)
- **Client/UI state**: local UI state (use a lightweight store such as Zustand when appropriate)

Rule of thumb:

- If data comes from the backend and needs caching/refetching → treat it as server state.
- If it’s purely UI state (open/closed, filters, selected row) → keep it client-side.

### Routing

Routing is handled client-side. The backend is configured to serve the SPA fallback so deep links work (React Router).

---

## Common tasks

### I changed the UI but the full platform doesn’t reflect it

If you are *not* using `bun run dev`, you are likely serving embedded static assets. Rebuild:

```/dev/null/rebuild.sh#L1-3
./build.sh
uv run fair serve --port 3000
```

### I’m getting CORS errors

Use backend dev mode:

```/dev/null/backend-dev-cors.sh#L1-1
uv run fair serve --dev --port 8000
```

Then run the frontend dev server on `:3000`.

---

## Suggested next docs

- `en/guides/development-workflow` — recommended overall developer workflow
- `en/guides/backend` — backend architecture (FastAPI + DB + plugin loading)
- `en/guides/plugins` — how plugins/extensions show up in the UI
- `en/sdk/overview` — SDK concepts and plugin system overview