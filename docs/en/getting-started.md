# Getting started

This quick guide explains how to install FAIR for local development. It assumes
that you have recent versions of [uv](https://docs.astral.sh/uv/) and
[Bun](https://bun.sh/) available on your system.

## 1. Clone the repository

```bash
git clone https://github.com/your-org/FAIR.git
cd FAIR
```

## 2. Install dependencies

Install Python dependencies using `uv` and frontend dependencies using Bun:

```bash
uv sync
cd frontend-dev
bun install
cd ..
```

## 3. Build everything

The project ships with a combined build script that produces the SPA assets,
Python package, and documentation:

```bash
./build.sh
```

The resulting artifacts are copied into `src/fair_platform/frontend/dist/` so
that the backend can serve them directly.

## 4. Run the backend

```bash
uv run fair --dev
```

The API is now available at `http://127.0.0.1:8000` and the frontend is mounted
at the root path. Visit `http://127.0.0.1:8000/docs/` to open the documentation
site that MkDocs generates.

## Next steps

- Explore the developer reference for details about the release process.
- Fork the repository and start experimenting with plugins.
- Share feedback on missing guides to help us expand the documentation.
