---
title: Dev Environment
description: Setting up a local development environment for the FAIR Platform
---
## Local Development Workflow

Use the dedicated dev command when iterating on the backend and frontend together. It starts the FastAPI API in headless mode with CORS enabled on port 8000 and runs the Vite dev server in `frontend-dev` at the same time:

```bash
fair dev
```

Common options:

```bash
# Backend on a custom port
fair dev --port 9000

# Backend only (no frontend dev server)
fair dev --no-frontend

# Serve bundled frontend alongside the dev frontend
fair dev --no-headless
```
