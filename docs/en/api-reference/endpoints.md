---
title: API Endpoints
description: Placeholder page listing Fair Platform API endpoint groups and conventions.
---

This page is a **placeholder** for the full Fair Platform API reference.

It exists to avoid 404s and to provide a stable URL that we can expand as endpoints stabilize.

## Conventions

- **Base path**: most endpoints are served under `/api/*` (for example: `http://localhost:3000/api/...`)
- **Auth**: token-based auth (JWT) is typically sent as:

```/dev/null/auth-header.txt#L1-1
Authorization: Bearer <token>
```

- **Formats**:
  - JSON for most requests/responses
  - Some submission/artifact uploads may use `multipart/form-data`

## Endpoint groups (to be documented)

The sections below reflect the *intended* organization of the API. Concrete routes, schemas, and examples will be added as the API routers are finalized.

### Health & Metadata

- `GET /api/health` — basic health check (if enabled)

### Authentication & Users

- Login / token issuance
- Current user session info
- User management (admins)

### Courses

- Create/list/update courses
- Enrollment/roster management

### Assignments

- Create/list/update assignments
- Configuration for accepted submission types and grading workflow

### Submissions

- Upload submission content
- List submissions per assignment
- Submission status / processing state

### Artifacts

Artifacts are the platform’s normalized internal representation of uploaded and derived content.

- Upload/list/download artifacts
- Derived artifacts (OCR output, parsed notebook, execution logs, etc.)

### Plugins / Extensions

- Discover available plugins
- Configure plugin settings
- Enable/disable plugins per course/assignment

## Next steps

- Read `en/api-reference/overview` for how the API is structured.
- Read `en/api-reference/authentication` for login/token details (placeholder).
- If you’re building extensions, start at `en/sdk/overview`.