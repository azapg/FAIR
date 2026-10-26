# 003 — Move browser sessions to an HttpOnly cookie

- **Status**: DONE
- **Commit**: 4210a60
- **Severity**: HIGH
- **Category**: Security
- **Rule**: react-doctor/auth-token-in-web-storage; socket/low-supply-chain-score
- **Estimated scope**: frontend auth/API/SSE, backend auth dependency/routes, tests, lockfile

## Problem

`frontend-dev/src/contexts/auth-context.tsx:124-135`, `frontend-dev/src/lib/api.ts:33-38`, and `frontend-dev/src/lib/sse-stream.ts:73-82` persist and read a bearer token from `localStorage`. Login also persists the token before `/auth/me` succeeds. `frontend-dev/bun.lock` pins vulnerable Axios 1.11.0.

## Target

React Doctor's canonical recipe is a server-set `HttpOnly` cookie. Keep bearer-header support for SDK/API clients, add cookie fallback for browser requests, set `HttpOnly`, `SameSite=Lax`, scoped path, and `Secure` outside local development. Axios/fetch must send credentials and never read a token from web storage. Logout and expired-session handling clear the cookie. Upgrade Axios to a currently patched release and verify the audit.

## Steps

1. Add additive cookie authentication to backend login, verification-session, current-user dependency, and logout without removing bearer compatibility.
2. Remove frontend token persistence and Authorization injection; use `withCredentials`/`credentials: "include"`.
3. Make login atomic: establish UI session only after `/auth/me` succeeds; clear the cookie on failure.
4. Add backend tests for cookie flags, cookie auth, logout, and bearer compatibility; add frontend auth tests.
5. Upgrade Axios and regenerate the Bun lockfile.

## Boundaries

- Do not break SDK bearer authentication.
- Do not expose the cookie value to JavaScript.

## Verification

- Backend auth tests, frontend tests/build, dependency audit, React Doctor, and a browser login/logout/session-expiry smoke test.
