---
title: Course copy and private templates
description: Reuse selected course authoring material safely without copying learner state.
---

Course staff can preview and create a new draft from an existing course. The preview
lists copied, transformed, skipped, and unsupported authoring objects before the
copy begins. Staff choose sections/content, assignments and linked rubrics,
gradebook structure, objective quizzes, and Flow definitions, then either clear
dates or shift them by an explicit whole-day offset.

Every destination has fresh IDs, is owned by the requester, starts with enrollment
disabled, and forces publishable material back to draft. Assignment, quiz,
grade-item, question-version, rubric, and Flow references are remapped to the new
course. Flow secrets are removed and its canonical definition hash is recomputed.

Learner enrollments, invite codes, submissions, attempts, comments, grade entries,
notifications, activity, and execution state are never copied. File items are
reported as unsupported until FAIR can duplicate protected storage without shared
deletion risk.

Copy jobs are durable and idempotent. Reusing a key with the same request returns
the same job; changing the request conflicts. A failed graph transaction leaves no
partial course, records the failure, and can be retried with the same key. Private
templates store a source reference plus selection and date defaults and invoke the
same engine; they are owner-only and not a public marketplace.
