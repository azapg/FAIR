# 007 — Make core controls and live updates accessible

- **Status**: DONE
- **Commit**: 4210a60
- **Severity**: HIGH
- **Category**: Accessibility
- **Rule**: react-doctor/control-has-associated-label and related semantic rules
- **Estimated scope**: 8-12 frontend files plus tests

## Problem

Primary chat composer controls, streamed status, elicitation, settings/search dialogs, submission feedback, and sidebar disclosures lack stable accessible names, announcements, focus handling, or native interactive semantics.

## Target

React Doctor's canonical recipe is to give every control visible text, `aria-label`, or `aria-labelledby`. Use native buttons for click actions; add `role=status`/`aria-live`/`role=alert` to asynchronous states; add dialog titles; move and restore focus for blocking elicitation; expose `aria-expanded`/`aria-controls` on disclosures.

## Steps

1. Label all icon-only chat composer, message, canvas, sources, and elicitation controls.
2. Announce streaming, errors, and required interactions without announcing every token.
3. Add hidden titles to desktop settings and command dialogs.
4. Replace clickable submission feedback text with a keyboard-operable button.
5. Add disclosure state to persistent navigation.
6. Add Testing Library accessibility/keyboard assertions for the critical controls.

## Verification

- Keyboard-only smoke test, accessible-name queries, focus-return checks, tests/build/React Doctor.
