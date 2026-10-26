---
title: Objective quizzes
description: Author reusable versioned questions, run guarded attempts, and release deterministic quiz points.
---

FAIR's initial quiz engine is a points-only objective assessment loop. It works
without an AI Extension and projects released scores through the same Gradebook 2.0
contract as assignments and manual items.

## Authoring

Course staff can create course-scoped question banks and author single-choice or
true/false questions. Authored content is immutable: an edit creates a new version,
while existing quizzes and started attempts continue to reference the exact version
they selected.

A quiz is created inside a course section as a typed `CourseItem`. Staff add fixed,
ordered question versions, choose positive point values, set an attempt limit and
either manual or immediate score release, then publish. Publishing requires at
least one question and creates or synchronizes one linked `GradeItem`.

Published question selection is locked. Closing a quiz blocks new attempt work but
keeps the course item and released results readable. Archived courses are read-only.

## Learner attempts

Only active student enrollments can start attempts. FAIR checks publish state,
course-item and section visibility, open/close windows, and the attempt limit. At
start, the attempt records its exact ordered question-version selection and point
values.

Answers use an idempotent upsert and submission is idempotent. Objective scoring is
deterministic: an answer receives its question's points only when its stable option
ID matches the immutable key; unanswered or incorrect questions receive zero.
Submitted attempts cannot be edited.

Student quiz and attempt responses never contain `correct_option_id`. A learner sees
correctness and points only after release. Staff authoring responses include the key
because those endpoints require course-management permission.

## Gradebook projection

Submission computes and stores the attempt score but does not by itself expose a
manual-release score. Immediate release occurs in the submission transaction;
manual release is a separate staff action. Release atomically upserts one released
`GradeEntry` with `source_type=quiz_attempt`, and its points must equal the stored
attempt score. A later released attempt supersedes an earlier attempt for the same
learner and quiz.

Gradebook totals therefore use only released canonical points. Unreleased quiz
attempts remain absent from the learner's grade entry and keep relevant totals
provisional rather than treating missing evidence as zero.

## Initial boundary

This reviewable slice intentionally excludes random question pools, essays and
manual question grading, partial credit, per-question feedback release rules,
timers, CSV import/export, drop-lowest rules, curves, arbitrary formulas, letter
grades, GPA, and analytics. The versioned records and generic course/grade linkage
are the extension points for those later features.
