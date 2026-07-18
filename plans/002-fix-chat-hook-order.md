# 002 — Remove the conditional chat hook

- **Status**: DONE
- **Commit**: 4210a60
- **Severity**: HIGH
- **Category**: Bugs & correctness
- **Rule**: react-doctor/rules-of-hooks
- **Estimated scope**: 2 files, small

## Problem

`frontend-dev/src/components/chat/chat-message.tsx:188-194` calls `useMemo` inside an IIFE that only renders when non-text events exist. Streaming the first tool or artifact event changes hook order.

## Target

Move the memoized phrase to the component top level, before conditional rendering, with stable primitive dependencies:

    const phraseBucket = Math.floor(taskTimer.elapsed / 3);
    const currentPhrase = React.useMemo(
      () => taskTimer.completed ? "Worked for" : getRandomProcessingPhrase(taskTimer.elapsed),
      [phraseBucket, taskTimer.completed],
    );

## Steps

1. Hoist the hook and formatting helper out of conditional JSX.
2. Add a rerender test that changes a message from text-only to event-rich.
3. Preserve the displayed timer/persona behavior.

## Verification

- Focused Vitest, full frontend tests/build, and React Doctor changed-scope scan.
