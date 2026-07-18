# 008 — Align chat and domain contracts with FAIR 1.0

- **Status**: DONE
- **Commit**: 4210a60
- **Severity**: HIGH
- **Category**: Maintainability & architecture
- **Rule**: Beyond the scan
- **Estimated scope**: 8-15 frontend files plus tests

## Problem

`/chat` and `/chat/live` maintain parallel orchestration stacks. `execution-client.ts` exports `V2Thread`/`V2Turn`, and Artifact contracts are duplicated between LMS hooks and Execution contracts. The canonical event adapter has no focused tests.

## Target

- Make `/chat` the canonical Thread/Turn/Execution experience; keep the scenario demo explicitly development-only if still useful.
- Rename first-party semantic `V2Thread`/`V2Turn` symbols to `Thread`/`Turn`.
- Extract shared UI message types from the mock Zustand store.
- Establish one canonical Artifact transport contract with explicit LMS view adapters where shapes differ.
- Add pure contract/projection tests.

## Steps

1. Separate shared UI contracts from prototype state.
2. Rename semantic v2 symbols and remove remaining legacy workflow wording from active surfaces.
3. Consolidate route ownership around canonical Execution.
4. Reconcile Artifact types using explicit adapters rather than competing same-name contracts.
5. Retire only files proven unreachable after consolidation.

## Verification

- Exact-string terminology audit, focused contract tests, full frontend tests/build, React Doctor, and live Execution smoke test.
