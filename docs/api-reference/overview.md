---
title: API Reference Overview
description: Overview of the Fair Platform HTTP API, how it’s structured, and how to authenticate.
---

Fair Platform exposes an HTTP API used by the web app and by external clients. This section explains what you can expect from the API and how to start making requests.

## Base URL

- When running locally via `fair serve`, the web UI typically runs on `http://localhost:3000`.
- The API is generally served under the `/api` prefix on the same origin in production-style mode.

If you’re running a backend-only/dev setup, your API may be hosted on a separate port (for example `http://localhost:8000/api`) depending on your CLI flags and environment.

## What the API provides

At a high level, the API is responsible for:

- Authentication and user/session management
- CRUD operations for core platform entities (courses, assignments, submissions, artifacts)
- Plugin/extension discovery and configuration (when enabled)
- Any platform-specific workflows that the frontend orchestrates

## Request/response format

- Requests and responses are JSON for most endpoints.
- File uploads (submissions/artifacts) may use `multipart/form-data` depending on the endpoint.

## Status codes

Typical status code behavior:

- `200` / `201`: Success
- `400`: Validation error / malformed request
- `401`: Missing/invalid authentication
- `403`: Authenticated but not allowed
- `404`: Resource not found
- `409`: Conflict (e.g., duplicate)
- `422`: Schema validation error (FastAPI-style)
- `500`: Unexpected server error

## Authentication

Fair Platform uses token-based authentication (JWT). In most deployments:

1. You authenticate via an auth endpoint (login).
2. You receive an access token.
3. You send the token on subsequent requests (usually via `Authorization: Bearer <token>`).

If you’re using the web UI, it manages tokens for you. For scripts and external clients, you’ll attach the header yourself.

## Quick examples

### cURL (authenticated request)

```/dev/null/curl-example.txt#L1-6
curl -H "Authorization: Bearer $FAIR_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:3000/api/health
```

### JavaScript (fetch)

```/dev/null/fetch-example.js#L1-18
const token = process.env.FAIR_TOKEN;

const res = await fetch("http://localhost:3000/api/health", {
  headers: {
    Authorization: `Bearer ${token}`,
  },
});

if (!res.ok) throw new Error(`Request failed: ${res.status}`);
console.log(await res.json());
```

## Next steps

- If you’re trying to call endpoints directly, start with:
  - `api-reference/authentication` (how to obtain tokens)
  - `api-reference/endpoints` (organized list of endpoints)
- If you’re building extensions, see the SDK docs:
  - `sdk/overview`
