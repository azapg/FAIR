---
title: SDK Schemas
description: Key data models used by the Fair Platform SDK (placeholder).
---

This page is a **placeholder** for the English documentation of Fair Platform SDK schemas.

The goal is to document the core data models you’ll encounter when building plugins (graders, transcribers/interpreters, validators, storage backends). As the SDK evolves, this page will be expanded with canonical field lists and examples.

## What are “schemas” in Fair Platform?

In Fair Platform, “schemas” refers to the **typed models** that describe:

- Platform entities you interact with (courses, assignments, submissions)
- Inputs to plugins (what data a plugin receives)
- Outputs from plugins (grades, feedback, derived artifacts)
- Artifact metadata and references to stored files/content

These models are designed to support:

- Validation (catch bad plugin input/output early)
- Reproducibility (consistent serialization for experiments)
- UI generation (forms and views derived from typed fields)

## Common schema concepts (high-level)

### Assignment
Represents what students are asked to submit and how it should be evaluated.

Typical information you can expect:
- Title / description / instructions
- Accepted submission types (e.g., PDF, images, ZIPs)
- Rubric or evaluation configuration (sometimes plugin-provided)
- Deadlines and settings that influence grading workflows

### Submission
Represents a student’s attempt for an assignment.

Typical information you can expect:
- Who submitted it (user/student reference)
- Which assignment it belongs to
- Timestamps and status
- Links to uploaded or derived artifacts
- Any processing logs or workflow state

### Artifact
Represents a stored piece of content (original upload or derived output).

Artifacts are used to normalize inputs for plugins. Examples:
- Original PDF upload
- OCR text extracted from an image
- Parsed notebook cells
- Execution logs from running student code
- Structured data extracted from a document

Typical artifact metadata:
- Type/kind (what it represents)
- Content reference (path, URL, object storage key, etc.)
- MIME or format information
- Provenance (how it was produced, by which plugin, from which source)

### Grade / Feedback (Result)
Represents the outcome of evaluation.

Typical information you can expect:
- Numeric score and/or rubric breakdown
- Comments or qualitative feedback
- Warnings/flags (plagiarism suspicion, formatting issues)
- Optional additional artifacts (annotated PDFs, traces, etc.)

## Where to find the source of truth

This page is intentionally light because the canonical definitions live in the SDK and backend models. Refer to the project source for up-to-date schema definitions in the SDK package and backend API models.

## Next pages

- `en/sdk/overview` — how the SDK fits into the platform
- `en/sdk/plugins` — plugin types and how to implement them
- `en/sdk/examples` — starter examples

If you tell me which plugin type you’re building first (grader vs transcriber vs validator), I can tailor the schema docs to the exact models you’ll touch most often.