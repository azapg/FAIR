# Fair Platform - AI Agent Instructions

## Project Architecture

The Fair Platform is a unified AI-powered grading platform with four main components:

- **CLI (`src/fair_platform/cli/`)**: Typer-based command-line interface (`fair serve`) that orchestrates the platform
- **Backend (`src/fair_platform/backend/`)**: Full FastAPI server with SQLAlchemy database, authentication, and modular API routers
- **Frontend (`frontend-dev/`)**: Vite+React SPA with TypeScript, built and embedded into the Python package
- **SDK (`src/fair_platform/sdk/`)**: Plugin system for extending platform with custom interpreters, graders, and validators

**Key Architectural Decision**: Frontend builds to static assets (`frontend-dev/dist/`) that get copied into the Python package (`src/fair_platform/frontend/dist/`) for single-binary deployment.

## Development Workflow

### Running the Platform
```bash
# Install dependencies and build
uv sync
./build.sh

# Run the full platform
fair serve --port 3000

# Frontend-only development (with backend dev server)
cd frontend-dev
bun install
bun run dev  # Runs on :3000, API calls proxy to :8000

# Backend-only development  
fair serve --dev --port 8000  # Enables CORS for frontend dev
```

### Build Process
- Frontend: `cd frontend-dev && bun run build` → static files in `frontend-dev/dist/`
- Copy: `./build.sh` copies `frontend-dev/dist/` to `src/fair_platform/frontend/dist/`
- Backend: FastAPI serves embedded frontend files when `--headless` flag is not used
- Package: `uv build` creates distributable Python package with embedded frontend

### Project Structure
- Root `pyproject.toml`: Package config with CLI entry point `fair = "fair_platform.cli.main:app"`
- `frontend-dev/`: Complete Vite+React frontend with Bun package manager
- `src/fair_platform/backend/`: Full FastAPI backend with database, auth, and API routers
- `src/fair_platform/sdk/`: Plugin system for extending platform functionality

## Frontend Conventions

### Tech Stack
- **React 19** with TypeScript and Vite build system
- **React Router v7** for client-side routing  
- **TanStack Query v5** for API state management with axios
- **Zustand** for client-side state management
- **Tailwind CSS v4** with `@tailwindcss/vite` plugin

### Typography System
- **Headings**: Remark serif font (`font-serif` class) - see `frontend-dev/public/fonts/remark/`
- **Body Text**: Host Grotesk sans-serif (`font-sans` class) - see `frontend-dev/public/fonts/host-grotesk/`  
- **Code**: System monospace (`font-mono` class)

### Component Patterns
- **Shadcn/ui**: Radix UI + CVA-based components in `src/components/ui/`
- **Styling**: Tailwind CSS v4 with custom CSS variables in `globals.css`
- **API Integration**: Axios instance in `src/lib/api.ts` with auth interceptors
- **Type Safety**: Strict TypeScript with plugin types from backend API

### Development Patterns
- **API Development**: Environment-based API URLs (`/api` in production, `http://localhost:8000/api` in dev)
- **Authentication**: JWT token storage in localStorage with automatic session handling
- **Plugin System**: Dynamic plugin loading with Pydantic schema-based settings
- **Query Keys**: TanStack Query with structured key factories (see `hooks/use-plugins.ts`)

## Backend Architecture

### FastAPI Structure
- **Main App**: `src/fair_platform/backend/main.py` with lifespan management and static file serving
- **Database**: SQLAlchemy with environment-based URLs (SQLite default, PostgreSQL via `DATABASE_URL`)
- **API Routers**: Modular routers in `backend/api/routers/` (auth, users, courses, assignments, plugins, etc.)
- **Plugin Loading**: Dynamic plugin discovery and registration via SDK

### Key Backend Patterns
- **CORS**: Conditional CORS middleware enabled with `--dev` flag for frontend development
- **SPA Fallback**: All unmatched routes serve `index.html` for React Router
- **Static Assets**: Frontend assets mounted at `/assets`, `/fonts`, `/data` routes
- **Database Init**: Automatic database initialization on startup via lifespan events

## SDK & Plugin System

### Plugin Architecture
- **Base Classes**: `BasePlugin` with settings field registration system
- **Plugin Types**: `transcriber`, `grader`, `validator` with TypeScript type definitions
- **Dynamic Settings**: Pydantic model generation from plugin settings fields
- **Storage Integration**: Pluggable storage backends via `load_storage_plugins()`

### Key SDK Files
- `src/fair_platform/sdk/plugin.py`: Base plugin system with settings management
- `src/fair_platform/sdk/schemas.py`: Core data models (Submission, Assignment, Artifact)
- `src/fair_platform/sdk/plugin_loader.py`: Plugin discovery and registration

## Key Files to Understand

- `src/fair_platform/cli/main.py`: CLI entry point with serve command orchestrating backend
- `src/fair_platform/backend/main.py`: FastAPI app with plugin loading, static serving, and API routing
- `frontend-dev/src/lib/api.ts`: Axios configuration with environment-based URLs and auth interceptors
- `frontend-dev/src/hooks/use-plugins.ts`: Plugin management with TanStack Query patterns
- `build.sh`: Build orchestration copying frontend dist to Python package
- `frontend-dev/vite.config.mjs`: Frontend build configuration with Tailwind plugin

## Development Patterns

- **TypeScript**: Strict typing with interface definitions for component props and API responses
- **State Management**: Zustand for client state, TanStack Query for server state with structured key factories
- **Plugin Architecture**: Pydantic-based settings with dynamic schema generation and runtime configuration
- **Build System**: Shell script orchestration with frontend asset embedding into Python package
- **Environment Handling**: Environment-specific API URLs and CORS policies

## Current Implementation Status

- **Backend**: Fully functional FastAPI server with SQLAlchemy, authentication, and modular API routers
- **Frontend**: Complete React SPA with routing, state management, and plugin integration
- **CLI**: Orchestrates full platform with headless and dev mode options
- **Plugin System**: Functional SDK with base classes, settings management, and dynamic loading
- **Database**: SQLite default with PostgreSQL support via environment variables

Focus on the CLI orchestration pattern and static frontend build approach when working with this codebase.
