# Fair Platform - AI Agent Instructions

## Project Architecture

The Fair Platform is a unified AI-powered grading platform with three main components:

- **CLI (`cli/`)**: Typer-based command-line interface (`fair serve`, `fair upload`) that orchestrates the platform
- **Backend (`backend/`)**: Python-based API server (currently minimal stub - `backend/main.py` just prints "Hello from backend!")  
- **Frontend (`platform/`)**: Next.js static-only application (no SSR/middleware/API routes) served by the backend

**Key Architectural Decision**: Frontend uses `next export` for static builds only - all backend logic stays in Python for deployment simplicity.

## Development Workflow

### Running the Platform
```bash
# Install and run via CLI (production approach)
pip install .
fair serve --port 3000

# Manual frontend development
cd platform
bun install
bun run dev
```

### Build Process
- Frontend: `bun run build && bun run export` → static files in `platform/out/`
- Backend: Serves exported frontend files (not yet implemented)
- CLI: Entry point defined in root `pyproject.toml` as `fair = "cli.main:app"`

### Project Structure
- Root `pyproject.toml`: CLI package configuration with Typer dependency
- `platform/`: Complete Next.js frontend with Bun package manager
- `backend/`: Minimal Python backend (early development stage)
- `build/` and `fair_platform.egg-info/`: Build artifacts (can ignore)

## Frontend Conventions

### Typography System
- **Headings**: Remark serif font (`font-serif` class) - see `platform/public/fonts/remark/`
- **Body Text**: Host Grotesk sans-serif (`font-sans` class) - see `platform/public/fonts/host-grotesk/`  
- **Code**: Geist Mono (`font-mono` class)

### Component Patterns
- **Shadcn/ui**: Radix UI + CVA-based components in `src/components/ui/`
- **Styling**: Tailwind CSS v4 with custom CSS variables in `globals.css`
- **Header Component**: Configurable header with user avatar dropdown (`src/components/header.tsx`)
- **Utility**: `cn()` function in `src/lib/utils.ts` for className merging

### Styling Architecture  
- Tailwind configured in `tailwind.config.ts` with font family mappings
- CSS variables system in `globals.css` with dark mode support via `.dark` class
- Button component uses CVA (class-variance-authority) for variant management

## Backend Architecture (In Development)

- Currently minimal - `backend/main.py` is a placeholder
- Planned: FastAPI/Flask server to serve static frontend and provide API endpoints
- Extension system: Empty `extensions/` folder indicates planned plugin architecture
- CLI serves as the orchestration layer between frontend and backend

## Key Files to Understand

- `cli/main.py`: CLI entry point showing current serve command implementation
- `platform/src/app/demo.tsx`: Homepage showcasing typography system and component patterns
- `platform/src/components/header.tsx`: Complex component showing prop patterns and TypeScript interfaces
- Root `README.md`: Project vision and current limitations

## Development Patterns

- **TypeScript**: Strict typing with interface definitions for component props
- **CSS-in-JS**: Avoided - uses Tailwind utility classes with occasional CSS variables  
- **State Management**: Not yet implemented (early stage project)
- **Testing**: Not yet implemented 
- **Extensions**: Planned plugin system (empty `extensions/` directory)

## Current Limitations

- Backend is not functional yet (placeholder implementation)
- CLI only starts frontend dev server, doesn't orchestrate full platform
- No authentication, database, or API layers implemented
- Extension system exists in concept but not implementation

Focus on the CLI orchestration pattern and static frontend build approach when working with this codebase.
