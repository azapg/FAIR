---
title: Authentication
description: How authentication works in the Fair Platform API (JWT tokens) and how to call endpoints securely.
---

This page explains how to authenticate when calling the **Fair Platform API** directly.

> This is currently a **placeholder** page to prevent 404s and provide a stable structure. As the API stabilizes, we’ll expand this into concrete endpoint-by-endpoint examples.

## Overview

Fair Platform uses **token-based authentication** (typically **JWT**). The general flow is:

1. Sign in using an authentication endpoint
2. Receive an **access token**
3. Include the token in subsequent requests using an `Authorization` header

## Sending the token

Most authenticated requests should include a header like:

```/dev/null/auth-header.txt#L1-1
Authorization: Bearer <ACCESS_TOKEN>
```

## Example (cURL)

```/dev/null/authenticated-request.sh#L1-6
FAIR_TOKEN="your-token-here"

curl -H "Authorization: Bearer $FAIR_TOKEN" \
     -H "Content-Type: application/json" \
     http://localhost:3000/api/health
```

## Example (JavaScript fetch)

```/dev/null/authenticated-request.js#L1-19
const token = process.env.FAIR_TOKEN;

const res = await fetch("http://localhost:3000/api/health", {
  headers: {
    Authorization: `Bearer ${token}`,
  },
});

if (!res.ok) throw new Error(`Request failed: ${res.status}`);
console.log(await res.json());
```

## Common status codes

- `401 Unauthorized`: Missing token, expired token, or invalid token
- `403 Forbidden`: Token is valid, but the user doesn’t have permission
- `422 Unprocessable Entity`: Request schema validation failed (common for JSON body issues)

## Security notes

- Do not hardcode tokens in source code or commit them to git.
- Prefer environment variables for development (`FAIR_TOKEN`, etc.).
- If you integrate third-party services (LLMs, storage), store API keys in environment variables or a secrets manager.

## Next steps

- `en/api-reference/overview`: API overview and concepts
- `en/api-reference/endpoints`: Endpoint directory (placeholder / coming soon)