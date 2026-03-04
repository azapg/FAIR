# GEMINI.md

## Project Overview
**The Fair Platform (FAIR)** is an open-source platform designed for experimenting with automatic grading systems using AI. It provides a modular environment to build, test, and compare grading approaches, supporting researchers and educators in improving assessment workflows.

### Core Architecture
- **Interpreters:** Parse and standardize submissions (PDFs, images, code) into structured artifacts.
- **Graders:** Evaluate submissions using configurable rubrics, AI models, or hybrid methods.
- **Artifacts:** Unified data types for storing submissions and results.
- **CLI (`fair`):** Main entry point for managing and serving the platform.

### Tech Stack
- **Backend:** Python 3.12+, FastAPI, SQLAlchemy, Alembic, Pydantic, Typer (CLI).
- **Frontend:** React 19, TypeScript, Vite, Tailwind CSS 4, Radix UI, TanStack Query, Zustand.
- **Package Management:** `uv` (Python), `bun` (Frontend).

---

## Building and Running

### Prerequisites
- **Python 3.12+**
- **uv** (Recommended Python manager)
- **Bun** (Required for frontend)

### Initialization & Build
The simplest way to set up the entire project is using the provided build script:
```bash
./build.sh
```
This script:
1. Syncs Python dependencies via `uv`.
2. Installs frontend dependencies in `frontend-dev` via `bun`.
3. Builds the frontend and copies the assets to the backend's static directory.
4. Builds the Python package.

### Running the Platform
Once built, use the CLI to start the server:
```bash
fair serve
```

### Testing
Tests are managed with `pytest`:
```bash
pytest
```
*Note: Some legacy tests might be failing; ensure new contributions include passing tests.*

---

## Development Conventions

### Python Standards
- **Style:** Follow PEP 8 guidelines.
- **Modularity:** Prioritize clean imports and modular design. Refer to `src/fair_platform/sdk` for core schemas and base classes.
- **CLI:** Commands are defined in `src/fair_platform/cli/main.py` using Typer.

### Frontend Standards
- **Framework:** React 19 with Vite.
- **Styling:** Tailwind CSS 4 and Radix UI components.
- **State Management:** Zustand for global state, TanStack Query for server state.
- **Location:** Source code resides in `frontend-dev/src`.
- **Casing:** Use camelCase for variables and functions, PascalCase for components. kebab-case is reserved for file names.

### Documentation
- Documentation is located in the `docs/` directory and is available in both English (`docs/en/`) and Spanish (`docs/es/`).
- The structure is managed by `docs/docs.json` (Mintlify).

### Git Workflow
- **Commit Messages:** Use imperative mood (e.g., "Add feature" not "Added feature").
- **Prefixes:** Use type prefixes such as `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, or `chore:`.
- **Issues:** Reference issue numbers in commit messages and pull requests.

---

## Directory Structure Highlights
- `src/fair_platform/`: Core backend logic and CLI.
- `frontend-dev/`: React frontend development environment.
- `docs/`: Multi-language documentation.
- `tests/`: Comprehensive test suite.
- `scripts/`: Utility scripts for OpenAPI generation and version syncing.
