# 005 — Lazy-load route graphs

- **Status**: DONE
- **Commit**: 4210a60
- **Severity**: HIGH
- **Category**: Performance
- **Rule**: Beyond the scan
- **Estimated scope**: 2-3 frontend files

## Problem

`frontend-dev/src/index.tsx:2-17` eagerly imports every route, pulling optional PDF.js, Rive, Markdown, and KaTeX graphs toward every entry page.

## Target

Use `React.lazy` dynamic imports for route pages, a stable accessible `Suspense` fallback, and preserve route paths. Ensure heavy PDF/chat assets live in route/feature chunks.

## Steps

1. Replace static page imports with lazy imports.
2. Wrap route rendering in `Suspense` with a non-jumping status fallback.
3. Add a route smoke test and inspect the production chunk graph.

## Verification

- Build and confirm separate route chunks.
- Compare initial compressed JS for `/login`, `/courses`, and `/chat`.
