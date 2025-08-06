# The Fair Platform

**Fair** is an extensible platform for exploring how AI and automation can improve grading, feedback, and education.  
It aims to provide a unified developer and user experience through a single CLI (`fair`) that can serve the full platform, manage workflows, and integrate modular extensions.

<!-- what a terrible explanation btw, I should explain more about the features and mission once i publish the paper or idk -->

> [!WARNING]
> This project is in early development. Most features are still being prototyped.

## What is Fair?

The Fair Platform is designed to be:

- **Flexible**: Teachers, researchers, or institutions can configure how grading and feedback works from simple scoring to AI-assisted evaluation.
- **Transparent**: Grading logic and model decisions can be inspected, adjusted, and audited.
- **Modular**: Features are implemented as plugins or extensions (e.g., agentic workflows, rag scripts, etc.).
- **Local-first**: You can run the platform from your own machine with a single command: `fair serve`.

## Running Fair

The platform is meant to feel simple and unified:

```bash
pip install fair-platform
fair serve --port 3000
```

Under the hood, this will:

* Serve the frontend (currently a static Next.js build)
* (Later) Launch the Python backend
* (Later) Load extensions/plugins dynamically

> [!WARNING]
> This is still not implemented, but you can use the command if you create a new Python enviorment and run `python -m pip install .`. You will then have accessto the fair cli in that venv

## Running in Development

Right now, the CLI only starts the frontend in dev mode:

```bash
fair serve --port 3000
```

Later, this will start both backend and frontend, and support plugins.

To run the frontend manually:

```bash
cd frontend
bun install
bun run dev
```

To build it:

```bash
bun run build
bun run export
```

Exported files live in `frontend/out/`, which the backend will serve.

## Frontend Notes

The frontend is currently a [Next.js](https://nextjs.org/) app, used **only for static builds**.
We do **not** use SSR, middleware, or API routes. This is a design decision to keep the backend entirely in Python and simplify deployment.

We use `next export` to build static assets, which are served by the backend.

This setup gives us:

* Fast iteration during development (`next dev`)
* Clean static builds for production
* Easy migration to Vite or raw React later
## Contributing

This project is not yet open to public contribution, but will be once a basic MVP is ready.
For now, feedback, suggestions, or ideas are welcome.
