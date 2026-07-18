# 001 — Keep course permission hooks unconditional

- **Status**: DONE
- **Commit**: 4210a60
- **Severity**: HIGH
- **Category**: Bugs & correctness
- **Rule**: react-doctor/rules-of-hooks
- **Estimated scope**: 2 files, small

## Problem

`frontend-dev/src/app/courses/page.tsx:32-33` short-circuits hook calls:

    const canCreateCourses = isAuthenticated && usePermission("create_course");
    const canJoinCourses = isAuthenticated && usePermission("join_course");

When session validation changes `isAuthenticated`, React sees a different hook count.

## Target

React Doctor's canonical recipe is to call every hook at the component top level on every render:

    const hasCreateCoursePermission = usePermission("create_course");
    const hasJoinCoursePermission = usePermission("join_course");
    const canCreateCourses = isAuthenticated && hasCreateCoursePermission;
    const canJoinCourses = isAuthenticated && hasJoinCoursePermission;

## Steps

1. Make the two permission calls unconditional.
2. Add a focused test that rerenders from unauthenticated to authenticated and proves the route does not throw.
3. Preserve the existing visibility behavior.

## Verification

- Run the focused Vitest test, full frontend tests, build, and React Doctor changed-scope scan.
- Confirm the create/join controls still follow capabilities.
