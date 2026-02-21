---
title: Installation (Developers)
description: Install FAIR Platform for development, build the frontend, and run the server locally.
---

This guide is for **developers** who want to run FAIR Platform from source (backend + embedded frontend).  
If you just want to *use* the platform, prefer the quick start:

- `pip install fair-platform`
- `fair serve`

## Requirements

You’ll need:

- **Python 3.12+**
- **uv** (Python package/dependency manager): https://docs.astral.sh/uv/getting-started/installation/
- **Bun** (frontend tooling): https://bun.com/get
- (Recommended) Git

## Clone the repository

```bash
git clone https://github.com/allanzapata/fair-platform.git
cd fair-platform
```

## Install dependencies

The project uses `uv` for Python dependencies.

```bash
uv sync
```

If you’re iterating on code and want commands to run inside the managed environment, you can prefix with `uv run`:

```bash
uv run python --version
```

## Build the platform (includes frontend)

FAIR’s architecture embeds the built frontend into the Python package so the backend can serve it as static assets.

The standard workflow is:

1. Build frontend → outputs to `frontend-dev/dist/`
2. Copy assets → into `src/fair_platform/frontend/dist/`
3. Run backend/CLI → serves those embedded assets

Use the repo build script:

```bash
./build.sh
```

If you’re on Windows and `./build.sh` doesn’t run in your shell, run it from a shell that supports it (for example Git Bash), or adapt the build steps manually:

- `cd frontend-dev && bun install && bun run build`
- copy `frontend-dev/dist/` → `src/fair_platform/frontend/dist/`

## Run the platform

After building, start the full platform:

```bash
uv run fair serve --port 3000
```

Then open:

- http://localhost:3000

### Useful flags

```bash
# Backend/API only (no embedded frontend)
uv run fair serve --headless

# Development mode (enables CORS so you can run the frontend dev server)
uv run fair serve --dev --port 8000
```

## Frontend-only development (recommended for UI work)

For fast UI iteration, run the frontend Vite dev server and proxy API calls to the backend.

Terminal 1 (backend dev server):

```bash
uv run fair serve --dev --port 8000
```

Terminal 2 (frontend dev server):

```bash
cd frontend-dev
bun install
bun run dev
```

Frontend will run on:

- http://localhost:3000

API requests should proxy to:

- http://localhost:8000

## Troubleshooting

### Python version issues

Confirm:

```bash
python --version
```

You must be on **Python 3.12+**.

### Port already in use

Pick a different port:

```bash
uv run fair serve --port 8080
```

### I updated the frontend but changes don’t show up

If you are running the embedded frontend (not `bun run dev`), you must rebuild:

```bash
./build.sh
```

Then restart `fair serve`.

## Next steps

- Read **Docs → Getting started** to understand the platform concepts:
  - `/en/getting-started/the-platform`
- Browse **Development → Releases**:
  - `/en/development/releases`
- Explore the SDK tab starting at:
  - `/sdk/overview`
