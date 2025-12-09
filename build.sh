#!/usr/bin/env bash

set -e

BUILD_DOCS=false
for arg in "$@"; do
  [[ "$arg" == "--docs" ]] && BUILD_DOCS=true
done

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

# Build docs if --docs flag is provided
if [ "$BUILD_DOCS" = true ]; then
    echo "Building docs..."
    
    if [ ! -d "docs" ]; then
        echo "Error: docs directory not found"
        exit 1
    fi
    
    cd docs
    bun run build
    cd ..
    
    if [ ! -d "docs/dist" ]; then
        echo "Error: docs/dist directory not found after build"
        exit 1
    fi
    
    echo "Docs build completed successfully"
    
    if [ -d "src/fair_platform/frontend/docs" ]; then
        rm -rf src/fair_platform/frontend/docs
    fi
    
    cp -r docs/dist src/fair_platform/frontend/docs
    echo "Docs assets copied to src/fair_platform/frontend/docs"
fi

echo "Building Python package..."
uv build

echo "Build completed successfully!"
