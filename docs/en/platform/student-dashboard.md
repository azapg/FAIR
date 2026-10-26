---
title: Student dashboard and Grades
description: See upcoming work, returned feedback, course progress, and released grades without exposing staff-only data.
---

The learner **Dashboard** brings together current work from every active student enrollment. Each course also has a learner-only **Grades** tab. Staff keep the existing **Gradebook** tab and cannot open a learner's private self view from a staff account.

## Dashboard

The dashboard shows:

- upcoming and overdue published assignments;
- recently returned scores and feedback;
- published announcements, materials, and assignments;
- completion of published course-content items; and
- each course's current server-computed grade.

Each source is projected independently. If one source cannot load, the dashboard labels that partial state and keeps the other sections usable.

Deadline comparisons use UTC instants and return an explicit presentation timezone. A private `CalendarEvent` owned by the learner can override an assignment due date with `source_type=assignment_due_override`, or close it with `source_type=assignment_cutoff`. Completed published assignment items are omitted from the work list. Future availability-rule evaluators should extend this projection rather than calculate deadlines in the browser.

## Grades

`GET /api/lms/courses/{course_id}/grades` is self-scoped to an active student enrollment. It consumes the same Gradebook 2.0 projection as the staff gradebook and returns only that learner's released evidence.

- **Current grade** includes released evidence only and is marked provisional while relevant entries or category weights are missing.
- **Released points** distinguish points currently earned and possible from unreleased work.
- **Contribution** is computed by the server for each released graded item in percentage points of the current total.
- **Missing** identifies a published assignment that has no released entry. Other unreleased item identities, points, and notes remain hidden.
- **Final grade** is available only for an archived course with a non-provisional canonical total.

The frontend never recalculates percentages or weighted totals. Points remain the only stored grade values; current percentages, weights, and contributions are derived by Gradebook 2.0.

## Privacy boundary

Both endpoints require a global learner role and reject any account with an active owner or assistant course membership. Dashboard activity is built from an allowlist of student-visible domain records, and links point only to existing self-authorized course and assignment routes. Draft assignments, draft scores, private notes, other students, and arbitrary activity payloads are never returned.
