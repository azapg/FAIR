# Extensions Workflow Migration Handoff

## Goal and product decisions
- Replace the deprecated in-process `sdk` plugin/workflow runtime with the HTTP-based extensions API.
- Keep the public concept as `plugin`, not `agent`.
- Rename legacy `validator` to `reviewer`.
- Workflows should be ordered step pipelines, but preserve a temporary role-based `plugins` compatibility view for the UI.
- Keep the existing log/event system and reuse it in the new protocol and SDK.
- Use `1 job = 1 workflow step`, orchestrated by the platform into `1 workflow run`.
- UI should consume a single aggregated workflow-run stream instead of switching between per-job streams.

## What was implemented

### SDK and protocol contracts
- Added shared plugin/pipeline contracts in `src/fair_platform/extension_sdk/contracts/plugin.py`.
- Exported those contracts from:
  - `src/fair_platform/extension_sdk/contracts/__init__.py`
  - `src/fair_platform/extension_sdk/__init__.py`
- Extended `FairExtension` in `src/fair_platform/extension_sdk/extension.py` so extensions can advertise plugin descriptors during registration via metadata.

### Default core extension
- Updated `src/fair_platform/extensions/core/main.py`.
- It now registers simple built-in transcriber, grader, and reviewer plugins:
  - `fair.core.transcriber.simple`
  - `fair.core.grader.simple`
  - `fair.core.reviewer.simple`
- It still keeps the existing rubric action.
- The core plugins now also emit incremental per-submission results using the new SDK helper instead of waiting only for one final batch result.

### Extensions-backed plugin catalog
- Added `src/fair_platform/backend/services/extension_catalog.py`.
- Replaced the legacy `/api/plugins` router implementation in `src/fair_platform/backend/api/routers/plugins.py`.
- `/api/plugins` now reads plugin descriptors advertised by registered extensions.
- `GET /api/plugins/{plugin_id}` was added as well.
- This route is still marked deprecated, but now acts as a compatibility shim over extension registration metadata.

### Workflow model and API
- Added `steps` JSON storage to `src/fair_platform/backend/data/models/workflow.py`.
- Replaced workflow API schemas in `src/fair_platform/backend/api/schema/workflow.py`.
- Replaced workflow router logic in `src/fair_platform/backend/api/routers/workflows.py`.
- New behavior:
  - Primary durable shape is `steps`.
  - Temporary compatibility field `plugins` is still returned.
  - Legacy DB workflows without `steps` are still read by deriving steps from `transcriber/grader/validator` columns.
  - `validator` is normalized to `reviewer` on read/write.

### Workflow run model and orchestration
- Added `step_states` and `request_payload` JSON fields to `src/fair_platform/backend/data/models/workflow_run.py`.
- Replaced workflow-run schemas in `src/fair_platform/backend/api/schema/workflow_run.py`.
- Replaced workflow-run router in `src/fair_platform/backend/api/routers/workflow_runs.py`.
- Added new services in `src/fair_platform/backend/services/workflow_runner.py`:
  - `WorkflowRunEventBroker`
  - `WorkflowRunner`
- `POST /api/workflow-runs` now exists and creates a pending run, snapshots the request payload, and starts background orchestration.
- `GET /api/workflow-runs/{id}/stream` now exists and emits a single aggregated SSE stream for the whole run.

### App initialization
- `src/fair_platform/backend/main.py` now initializes:
  - `app.state.workflow_run_event_broker`
  - `app.state.workflow_runner`
- The workflow-runs router also has lazy fallback initialization for tests where lifespan state is not present.

### Frontend updates
- Renamed frontend plugin role usage from `validator` to `reviewer` in:
  - `frontend-dev/src/hooks/use-plugins.ts`
  - `frontend-dev/src/store/workflows-store.ts`
  - `frontend-dev/src/app/assignment/components/sidebar/workflows-sidebar.tsx`
  - `frontend-dev/src/app/courses/tabs/workflows-tab.tsx`
  - `frontend-dev/src/app/assignment/components/submissions/submissions.tsx`
  - `frontend-dev/src/i18n/locales/en.json`
  - `frontend-dev/src/i18n/locales/es.json`
- Switched run initiation in the assignment workflow sidebar from `/api/sessions` to `/api/workflow-runs`.
- Switched live log streaming from the old websocket session path to the new workflow-run SSE path in:
  - `frontend-dev/src/contexts/session-socket-context.tsx`
  - `frontend-dev/src/app/assignment/components/sidebar/execution-logs-view.tsx`

### Migration
- Added Alembic migration:
  - `src/fair_platform/backend/alembic/versions/20260305_0014_extensions_workflow_pipeline.py`
- It adds:
  - `workflows.steps`
  - `workflow_runs.step_states`
  - `workflow_runs.request_payload`

## Current execution design

### Dispatcher vs orchestrator
- The existing dispatcher is still dumb and unchanged in principle.
- It still sends one job to one extension.
- The new `WorkflowRunner` is the platform orchestrator:
  - create first step job
  - wait for child job result via `JobQueue.subscribe_updates`
  - persist events into `workflow_run.logs.history`
  - update `workflow_run.step_states`
  - merge outputs into per-submission pipeline state
  - enqueue the next step

### Persistence
- Full normalized event persistence was not implemented as a separate `workflow_run_events` table.
- Instead, the current implementation persists aggregated events in `workflow_runs.logs["history"]`.
- This reuses the existing log system and is enough for replay in the current UI.
- Step execution state is stored in `workflow_runs.step_states`.
- Step request snapshot is stored in `workflow_runs.request_payload`.

### Result persistence
- The orchestrator persists step outputs into the deprecated `SubmissionResult` table as a bridge:
  - transcriber -> `transcription`
  - grader -> `score`, `feedback`
  - reviewer -> nested data under `grading_meta["review"]`
- This is pragmatic, not final architecture.
- The orchestrator also now updates `Submission` rows while the workflow runs:
  - step start updates statuses (`transcribing`, `grading`, `processing`)
  - transcriber completion marks submissions `transcribed`
  - grader completion updates `draft_score` / `draft_feedback` and marks submissions `graded`
  - reviewer completion marks submissions `needs_review` when flags are returned

## Important limitations / unfinished work

### Legacy runtime is still present
- The old session manager and in-process plugin execution path still exists in `src/fair_platform/backend/services/session_manager.py`.
- The old `/api/sessions` route still exists.
- The new workflow-run path is wired and used by the updated frontend run button, but the legacy code was not removed yet.

### No dedicated workflow_run_events table
- Plan originally wanted append-only event rows.
- Current implementation stores history in `workflow_runs.logs`.
- If you want stronger replay/query semantics, this is the next structural backend change.

### No full multi-step end-to-end integration test yet
- There is no automated test that registers a live extension plugin, runs a real multi-step workflow, and asserts chained execution plus SSE output.
- The current tests cover the new plugin catalog and workflow-run creation/read surface, not the whole orchestration loop.

### Ordered steps are still not a true frontend editing model
- Backend stores workflows as `steps`, but the current UI still behaves mostly as `transcriber/grader/reviewer` slots.
- Reordering, duplicate plugin types, and arbitrary step pipelines are not implemented in the editor yet.

### Reviewer status is still modeled as `processing`
- There is no dedicated `reviewing` submission status in the current enum/model/frontend.
- Reviewer step start currently maps to `processing` to avoid another migration in this pass.

### Incremental result protocol is present but still minimal
- Added a new nonterminal `submission_result` job update event.
- The runner consumes it and persists per-submission results as they arrive.
- However, there is still no richer protocol for partial failures, retries, or per-submission terminal summaries beyond the streamed payloads.

### Frontend compatibility layer is partial
- The workflow API still returns `plugins` for compatibility.
- The frontend store/types are still role-map based, not true ordered-step editing.
- The new backend supports ordered `steps`, but the current UI still mainly edits role slots.

### Legacy plugin DB model remains
- `src/fair_platform/backend/data/models/plugin.py` and legacy plugin hash columns on `Workflow` still exist.
- Reads from old workflows still work via compatibility logic.
- Runtime execution is supposed to move to extensions, but no cleanup has been done yet.

## Files most relevant for the next agent

### Backend core
- `src/fair_platform/backend/api/routers/plugins.py`
- `src/fair_platform/backend/api/routers/workflows.py`
- `src/fair_platform/backend/api/routers/workflow_runs.py`
- `src/fair_platform/backend/services/extension_catalog.py`
- `src/fair_platform/backend/services/workflow_runner.py`
- `src/fair_platform/backend/main.py`

### Backend models/schemas
- `src/fair_platform/backend/data/models/workflow.py`
- `src/fair_platform/backend/data/models/workflow_run.py`
- `src/fair_platform/backend/api/schema/plugin.py`
- `src/fair_platform/backend/api/schema/workflow.py`
- `src/fair_platform/backend/api/schema/workflow_run.py`

### SDK / extension side
- `src/fair_platform/extension_sdk/contracts/plugin.py`
- `src/fair_platform/extension_sdk/extension.py`
- `src/fair_platform/extensions/core/main.py`

### Frontend
- `frontend-dev/src/hooks/use-plugins.ts`
- `frontend-dev/src/store/workflows-store.ts`
- `frontend-dev/src/app/assignment/components/sidebar/workflows-sidebar.tsx`
- `frontend-dev/src/contexts/session-socket-context.tsx`
- `frontend-dev/src/app/assignment/components/sidebar/execution-logs-view.tsx`

## Tests and validation already run
- Backend tests:
  - `uv run --all-extras pytest -q tests/test_extensions_api.py tests/test_workflow_runs_api.py`
  - Result when last run: `12 passed`
- Frontend build:
  - `bun run build`
  - Build succeeded

## New tests added
- `tests/test_extensions_api.py`
  - added coverage that extension-registered plugins are visible through `/api/plugins`
- `tests/test_workflow_runs_api.py`
  - added coverage that the new `POST /api/workflow-runs` endpoint returns a pending run for a step-based workflow
  - added coverage that grader persistence updates submission draft fields/status

## Suggested next steps
1. Add a real end-to-end orchestration test using a registered mock extension plugin and assert chained step execution.
2. Decide whether to add a real `workflow_run_events` table or continue with `workflow_runs.logs.history`.
3. Remove or retire the old in-process session manager path once the extensions-backed path is trusted.
4. Refactor the frontend workflow editor from role-map storage to true ordered-step editing.
5. Add a real end-to-end test for incremental `submission_result` streaming and live submission table refresh.
