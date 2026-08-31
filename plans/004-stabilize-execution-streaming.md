# 004 — Bound Execution streaming work and lifecycle

- **Status**: DONE
- **Commit**: 4210a60
- **Severity**: HIGH
- **Category**: Performance
- **Rule**: Beyond the scan; react-doctor/effect-needs-cleanup
- **Estimated scope**: 5-7 frontend files plus tests

## Problem

Every `message.delta` in `frontend-dev/src/hooks/use-execution-chat.ts:120-142` rerenders `LiveChatPage`, remaps all messages, and reparses historical message content. The mock chat uses whole-store subscriptions. The hook owns an AbortController but has no unmount cleanup.

## Target

- Abort an active stream on unmount using `useEffect(() => stop, [stop])`.
- Memoize message rows and pass stable callbacks/objects so unchanged historical rows do not render per delta.
- Replace whole-Zustand-store subscriptions with selectors/shallow selection.
- Extract pure Execution-event projection so it can be tested without mounting the route.

## Steps

1. Add lifecycle cleanup and pure event-state projection tests.
2. Introduce memoized live/mock message row boundaries with stable props.
3. Narrow Zustand subscriptions in chat page/sidebar/playback.
4. Preserve event ordering, interactions, artifacts, status, and auto-scroll.

## Verification

- Tests/build/React Doctor.
- Profile a 20-message conversation: unchanged rows and sidebar must not rerender for each delta; record before/after commits.
