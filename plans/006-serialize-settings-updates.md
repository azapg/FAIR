# 006 — Prevent concurrent settings overwrites

- **Status**: DONE
- **Commit**: 4210a60
- **Severity**: MEDIUM
- **Category**: Bugs & correctness
- **Rule**: Beyond the scan
- **Estimated scope**: 2 frontend files plus tests

## Problem

`frontend-dev/src/hooks/use-user-settings.ts:206-223` derives full replacement objects from a render-time snapshot. Quick edits can send competing replacements and lose the first accepted change.

## Target

Serialize user-settings mutations with a shared TanStack mutation scope, derive each update from the latest query-cache value when execution begins, and update/rollback the canonical cache deterministically.

## Steps

1. Centralize the settings mutation and shared scope id.
2. Derive path/patch changes from `queryClient.getQueryData` at mutation execution time.
3. Add a deferred-request test proving rapid independent edits survive in order.

## Verification

- Focused settings tests, full frontend tests/build.
