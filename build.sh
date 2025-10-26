#!/usr/bin/env bash

set -e
echo "Building frontend..."

if [ ! -d "frontend-dev" ]; then
    echo "Error: frontend-dev directory not found"
    exit 1
fi

cd frontend-dev
bun run build
cd ..

if [ ! -d "frontend-dev/dist" ]; then
    echo "Error: frontend-dev/dist directory not found after build"
    exit 1
fi

echo "Frontend build completed successfully"

if [ -d "src/fair_platform/frontend/dist" ]; then
    rm -rf src/fair_platform/frontend/dist
fi

cp -r frontend-dev/dist src/fair_platform/frontend/dist
echo "Frontend assets copied to src/fair_platform/frontend"

echo "Building documentation..."
uvx --with mkdocs-static-i18n mkdocs build --config-file mkdocs.yml

if [ ! -d "site" ]; then
    echo "Error: MkDocs build did not produce a site directory"
    exit 1
fi

DOCS_DEST="src/fair_platform/frontend/dist/docs"

if [ -d "$DOCS_DEST" ]; then
    rm -rf "$DOCS_DEST"
fi

mkdir -p "$(dirname "$DOCS_DEST")"
cp -r site "$DOCS_DEST"
rm -rf site

echo "Documentation copied to $DOCS_DEST"

echo "Building Python package..."
uv build

echo "Build completed successfully!"
