# PostgreSQL Compatibility PR TODO

## Context
This repository has historically been developed and tested mostly with SQLite. We now need to make PostgreSQL a first-class backend and remove schema/migration assumptions that only work reliably on SQLite.

This PR is the coordination point for that work. If you are a new agent joining this effort, start here first.

## Why this PR exists
- PostgreSQL support is partial and inconsistent.
- JSON/JSONB handling is mixed across models.
- Runtime startup currently calls `create_all`, which can bypass Alembic migration history.
- CI and tests are SQLite-only today, so PostgreSQL breakages are not caught early.
- There are signs of migration/model drift (notably plugin PK/FK history).

## Current Known Risks
- JSON columns are not consistently mapped to JSONB on PostgreSQL.
- Fresh DB creation and migrated DBs may diverge due to `create_all` vs Alembic.
- Migration path around plugin identifiers may be inconsistent across branch histories.
- Production migration risk is higher without PostgreSQL integration tests.

## Scope
In scope:
- ORM type normalization for PostgreSQL-safe behavior.
- Alembic migration fixes and reconciliation.
- PostgreSQL migration tests and CI coverage.
- Startup flow changes to avoid schema drift in runtime.

Out of scope:
- Major business logic refactors unrelated to DB compatibility.
- Broad API redesign.

## Execution Plan

### 1) Establish DB contract (owner: platform/backend)
- [x] Confirm supported PostgreSQL versions (target: 15/16).
- [x] Define JSON policy: JSONB on PostgreSQL for JSON document columns.
- [x] Define schema-change policy: Alembic-only in non-test environments.

### 2) Normalize ORM model types (owner: backend/data models)
- [x] Introduce shared JSON type helper (e.g., `JSON().with_variant(JSONB, "postgresql")`).
- [x] Apply helper to all JSON document columns:
  - `assignments.max_grade`
  - `workflows.transcriber_settings`
  - `workflows.grader_settings`
  - `workflows.validator_settings`
  - `workflow_runs.logs`
  - `plugins.meta`
  - `plugins.settings_schema`
  - `artifacts.meta`
  - `submission_results.grading_meta` (legacy/deprecated but still present)
- [x] Review timestamp columns for consistency (`DateTime(timezone=True)` vs UTC-naive policy).
- [x] Add/align `server_default` where DB-level defaults are required.

### 3) Reconcile migration history drift (owner: alembic/migrations)
- [x] Audit plugin PK/FK chain from baseline to head and make it deterministic.
- [x] Add corrective migration(s) for plugin key/constraint consistency.
- [x] Ensure migration scripts are safe on both PostgreSQL and SQLite where needed.
- [x] Verify branch merge points and down_revision graph are valid from baseline to head.

### 4) Add JSON -> JSONB migrations (owner: alembic/migrations)
- [x] Create migration converting target columns to JSONB on PostgreSQL (`USING ...::jsonb`).
- [x] Keep SQLite path no-op/type-compatible.
- [x] Add selective GIN indexes only if query patterns justify them.

### 5) Stop runtime schema auto-creation drift (owner: backend/app startup)
- [x] Remove/guard production startup path using `Base.metadata.create_all`.
- [x] Keep optional bootstrap mode only for explicit local/test scenarios.
- [x] Update docs: startup requires `alembic upgrade head`.

### 6) Add PostgreSQL test and CI coverage (owner: tests/ci)
- [x] Add PostgreSQL integration fixture (service container or equivalent).
- [x] Ensure test DB setup uses Alembic migrations (not `create_all`) for integration path.
- [x] Add CI matrix:
  - SQLite fast suite
  - PostgreSQL suite
- [x] Add regression tests for:
  - JSONB storage validation on PostgreSQL
  - FK integrity/cascades
  - Plugin hash PK/FK behavior
  - Migration rehearsal from stale/new SQLite snapshots to head

### 7) Rollout readiness (owner: release/platform)
- [x] Stage migration rehearsal on PostgreSQL with realistic data.
- [x] Document deployment order (backup, migrate, validate, cutover).
- [x] Document rollback strategy for non-trivial data transforms.

## Suggested Work Order for Parallel Agents
1. Agent A: ORM JSON/JSONB normalization.
2. Agent B: Migration drift audit + corrective revisions.
3. Agent C: PostgreSQL test harness + CI matrix.
4. Agent D: Startup flow/docs cleanup (`create_all` policy).

## Definition of Done
- [x] All intended JSON document columns resolve to JSONB on PostgreSQL.
- [x] `alembic upgrade head` yields schema consistent with ORM metadata.
- [x] PostgreSQL CI job passes.
- [x] Runtime no longer silently mutates schema in production paths.
- [x] Migration path is reproducible for fresh and legacy DBs.

## Notes for Incoming Agents
- Keep changes incremental and migration-safe.
- Do not rewrite old migrations unless absolutely necessary; prefer additive corrective revisions.
- Prefer adding regression tests with every schema change.
- Call out any irreversible migration explicitly in PR notes.

## Implemented in This Branch (2026-02-24)
- Added shared JSON document type helper in models (`JSON` + PostgreSQL `JSONB` variant).
- Normalized JSON document fields across models to use the shared type.
- Added DB contract notes in backend README (PostgreSQL target, JSONB policy, Alembic-first schema policy).
- Patched migration `39361b552edd` to enforce plugin hash uniqueness on PostgreSQL before creating plugin-hash foreign keys.
- Added migration `20260224_0011` to:
  - Reconcile plugin primary key to `plugins.hash` on PostgreSQL.
  - Convert JSON columns to JSONB on PostgreSQL with `USING ...::jsonb`.
  - Keep non-PostgreSQL paths as no-op for type conversion.
