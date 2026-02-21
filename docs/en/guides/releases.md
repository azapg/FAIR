---
title: Releases (Guide)
description: How releases work in Fair Platform, including versioning, build artifacts, and publishing (placeholder).
---

This page documents the **release process** for Fair Platform.

> Status: This is an **initial placeholder** intended to prevent 404s and establish a stable URL structure.
> It will be expanded as the release pipeline and conventions are finalized.

---

## What counts as a “release” in Fair Platform?

A release generally means shipping a new version of the platform that users can install and run. In practice, this may include:

- Publishing a new version of the Python package to **PyPI** (`fair-platform`)
- Tagging a version in **git**
- Updating release notes / changelog
- Ensuring the **frontend build** is embedded into the Python package (when shipping the full UI experience)
- Running a clean install smoke test:
  - `pip install fair-platform`
  - `fair serve`

---

## Key packaging/build detail: embedded frontend assets

Fair Platform is designed so that the frontend build outputs static files that get copied into the Python package.

High-level workflow:

1. Build frontend → outputs to `frontend-dev/dist/`
2. Copy assets → into `src/fair_platform/frontend/dist/`
3. Build Python package → includes embedded frontend assets
4. `fair serve` serves the embedded frontend (unless `--headless`)

This is important for releases: if you publish without embedding updated assets, users may see:

- missing assets
- outdated UI
- broken SPA routing

---

## Versioning (placeholder)

This section will describe:

- The project’s versioning scheme (e.g. SemVer or variants)
- When to bump major/minor/patch
- How breaking changes are communicated (API, SDK, CLI, frontend)

For now, treat version bumps as a deliberate step that should align with the scope of changes.

---

## Expected release workflow (high-level)

This is the conceptual flow that will be finalized into a step-by-step checklist:

1. **Prepare changes**
   - Make sure PRs are merged
   - Verify CI is green
   - Ensure docs are updated where needed

2. **Update version**
   - Update the project version in the appropriate packaging config
   - Confirm the changelog/release notes reflect the changes

3. **Build**
   - Build frontend and embed it into the package
   - Build Python distributions (sdist/wheel)

4. **Tag & publish**
   - Create a git tag for the release
   - Publish artifacts to PyPI
   - Create a GitHub release (if used)

5. **Post-release verification**
   - Install from PyPI in a clean environment and run `fair serve`
   - Verify UI loads and API works
   - Verify docs navigation (if docs are deployed alongside)

---

## Pre-release checklist (placeholder)

Before publishing:

- [ ] Confirm **frontend** is rebuilt and embedded into the package
- [ ] Confirm `fair serve` works locally using the release build
- [ ] Confirm docs pages referenced in navigation exist (no 404s)
- [ ] Confirm SDK/documentation changes are consistent with the implementation
- [ ] Confirm authentication + database initialization works on a clean run
- [ ] Confirm platform starts in:
  - [ ] default mode (UI + API)
  - [ ] `--headless` mode (API only)

---

## Common failure modes

### UI changes don’t appear after installing the new version
Likely causes:

- The embedded frontend wasn’t rebuilt/copied into the package before building the wheel/sdist.
- The build pipeline copied the wrong `dist/` directory.

### Works locally, breaks after publish
Likely causes:

- Transitive dependency differences between local and published environments
- Missing packaged files (MANIFEST / include rules)
- Environment-specific assumptions (paths, ports, OS differences)

### Docs navigation links 404 after release
Likely causes:

- Navigation references pages that weren’t committed or published
- Paths changed (e.g., moving pages under `en/` / `es/`) without updating navigation

---

## Related pages

- Release automation (docs section): `/en/development/releases`
- Development workflow: `/en/guides/development-workflow`
- Installation (developers): `/en/guides/installation`

Spanish counterpart (placeholder):

- `/es/guides/releases`

---

## What will be added here next

Planned expansions:

- Exact commands for building distributions and verifying artifacts
- How versions are stored/updated in the repository
- CI/CD pipeline details (what runs on tags, what publishes to PyPI)
- Rollback strategy
- Changelog conventions
- “Release candidate” workflow (if adopted)