---
title: LMS foundation primitives
description: Persistent contracts shared by FAIR's course builder, dashboards, gradebook, quizzes, and course copy features.
---

# LMS foundation primitives

FAIR's LMS foundation is a normalized persistence contract for the next teaching features. It deliberately adds no end-user interface and no feature API. Feature services should build on these records instead of creating parallel course, grade, progress, identity, calendar, or audit tables.

## Core invariants

### Course structure

`CourseSection` is an ordered container in one course. `CourseItem` is an ordered child that can represent a page, file, link, assignment, quiz, forum, or a future activity type.

- Positions are stable non-negative integers and unique within their parent. Reordering should update all affected positions in one transaction.
- Visibility is explicit: `draft`, `published`, or `hidden`.
- A typed resource link uses the pair `resource_type` and `resource_id`. Both are present or both are absent. Core does not import or own future quiz, forum, or lesson models.
- `payload_schema_uri` and `payload` hold versioned, type-specific display/configuration data. They are not an unversioned replacement for normalized feature data.
- Composite foreign keys prevent an item from pointing to a section in another course.
- Copyable sections and items retain `copied_from_id`. A course-copy service must remap resource IDs rather than silently carrying links to the source course.

### Gradebook

`GradeCategory`, `GradeItem`, and `GradeEntry` establish one points-only gradebook contract.

- `GradeItem.max_points` and `GradeEntry.points_earned` are finite numeric point values. FAIR never persists percentages, letters, or pass/fail labels as grade values. Those are derived presentations or policy outputs.
- Category and item weights, aggregation strategy, drop rules, extra-credit behavior, and similar calculations live in explicit policy metadata. Policy must not mutate the stored points.
- Categories may form a course-scoped hierarchy. Items cannot attach to categories in another course.
- Each learner has at most one current entry per grade item. The entry is `graded`, `missing`, or `excused`; missing and excused entries do not invent a zero-point score.
- Release state is separate from grading state. Released entries require `released_at`; unreleased entries cannot carry it.
- `source_type`, `source_id`, and `source_version` identify the fact projected into the gradebook. Assignment return should write only the returned/published points, atomically, with the submission as source. Draft submission scores never belong in `GradeEntry`.
- Until the assignment migration is complete, `Submission.published_score` remains the compatibility source. Gradebook work must assert parity rather than choosing one value opportunistically.
- Composite foreign keys require both the grade item and the enrolled learner to belong to the entry's course.

### Completion and availability

`CompletionRule` and `AvailabilityRule` are ordered, typed predicates with versionable JSON configuration. `UserItemCompletion` is the current learner projection (`not_started`, `in_progress`, or `completed`) and may retain typed source evidence.

The foundation does not define rule evaluation. Future services must publish supported `rule_type` values, validate each configuration, and update projections transactionally. Cross-course items and users without an enrollment are rejected by database constraints.

### Institutions and groups

`Organization`, `OrganizationMembership`, `Cohort`, `CohortMembership`, `CourseGroup`, and `CourseGroupMembership` provide distinct institutional and course-local scopes.

- A cohort member must already be a member of the same organization.
- A course-group member must already be enrolled in the same course.
- `ExternalIdentifier` maps a user, course, or cohort to an identifier from a named external system. The mapping is organization-scoped and identifies exactly one FAIR subject.
- External identifiers are integration keys, not authentication credentials. Sync services remain responsible for authorization, conflict handling, and lifecycle policy.

### Calendar, notifications, and activity

`CalendarEvent` supports private and course-visible events, timezone labels, recurrence metadata, typed sources, and copy provenance. `NotificationPreference` records a user's delivery choice per channel and event type. Both retain nullable source pairs so course copy can remap generated records.

`ActivityEvent` is an append-only fact with actor, course, organization, object, source, schema, and payload fields. ORM guards and database triggers reject updates and deletes. Corrections must be represented by a new event that references the earlier fact in its payload; event payloads should also record course-copy provenance when no dedicated `copied_from_id` exists.

Activity events do not replace domain transactions or the execution event stream. Feature services decide which completed LMS actions deserve an activity event and must write them in the same transaction as the authoritative state whenever possible.

## Intended rollout

1. **Course builder (A1):** create sections/items and validate type-specific payloads and resource ownership.
2. **Student dashboard (A2):** consume published items, released grades, completion projections, calendar events, and activity events.
3. **Gradebook 2.0 (A3):** create categories/items, project returned assignment points, calculate derived views, and expose history separately from the current `GradeEntry` projection.
4. **Quiz engine (A4):** attach quiz resources through the existing typed course-item and grade-item seams.
5. **Course copy (A7):** clone copyable records, preserve `copied_from_id`, remap typed sources/resources, and emit an activity event describing the mapping.

## Non-goals

This foundation does not provide CRUD endpoints, UI, permissions, quiz questions, grade calculations, completion evaluation, notification delivery, SIS synchronization, course-copy execution, automatic activity logging, or historical grade revisions. Each feature PR must add its behavior and authorization without weakening these storage invariants.

The migration is explicit and supports both SQLite and PostgreSQL. JSON documents use JSON on SQLite and JSONB on PostgreSQL; cross-scope protections use portable composite foreign keys rather than database-specific application assumptions.
