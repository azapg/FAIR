#!/usr/bin/env bash

set -e

info() {
    echo "==> $1"
}

warn() {
    echo "⚠️  $1"
}

error() {
    echo "❌ $1"
}

info "Checking build prerequisites..."

if ! command -v bun >/dev/null 2>&1; then
    error "Bun is required for frontend dependencies and build."
    echo "   Install Bun from https://bun.sh/ and run this script again."
    exit 1
fi

if command -v uv >/dev/null 2>&1; then
    info "Syncing Python dependencies with uv..."
    uv sync
else
    warn "uv not found; falling back to Python/pip for dependency installation."
    python -m pip install -e .
fi

info "Installing frontend dependencies with Bun..."

if [ ! -d "frontend-dev" ]; then
    echo "Error: frontend-dev directory not found"
    exit 1
fi

cd frontend-dev
bun install

info "Building frontend..."
bun run build
cd ..

if [ ! -d "frontend-dev/dist" ]; then
    echo "Error: frontend-dev/dist directory not found after build"
    exit 1
fi

info "Frontend build completed successfully"

if [ -d "src/fair_platform/frontend/dist" ]; then
    rm -rf src/fair_platform/frontend/dist
fi

cp -r frontend-dev/dist src/fair_platform/frontend/dist
echo "Frontend assets copied to src/fair_platform/frontend"

info "Building Python package..."
if command -v uv >/dev/null 2>&1; then
    uv build
else
    warn "uv not found; falling back to python -m build."
    python -m build
fi

info "Build completed successfully!"
