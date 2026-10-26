# Google sign-in verification

Validated on 2026-10-26 for PR #260. Real Google sign-in was confirmed by Allan
on the separate localhost instance. The checks below use synthetic identities;
no production users, credentials, emails, or courses were modified.

## Browser checks

The actual production-built React app and FastAPI backend ran on localhost:8010.
A simulated provider ran on 127.0.0.1:8010, so browsers crossed sites before
returning to the real callback. Discovery, code exchange, PKCE, signature/issuer/
audience/nonce validation, database writes, and HttpOnly cookie sessions remained
real; only Google's HTTP responses and consent page were simulated.

| Case | Observed result |
| --- | --- |
| New Google user | Returned to Courses as a normal user without a local password. |
| Reload and logout | Reload retained the session; logout made `/auth/me` return 401. |
| Email matches an existing password account | Clear link-required message; no duplicate account or session created. |
| Incorrect linking password, then retry | Error stayed in the dialog; a correct password allowed the redirect. |
| Connect an existing professor | Same user ID and instructor role; the existing course remained available. |
| Sign in again after linking | Google returned to that same account; no new user was created. |
| Registration requires an invite | Uninvited signup was denied without a session. |
| Cancel at provider | Returned to a usable login form with a cancellation message. |
| Invalid nonce | Rejected the identity; no session was issued. |
| Provider unavailable, then retry | Login showed an error; the same button worked once the provider recovered. |
| Invitation fragment | Code moved from the URL into registration state; Google signup succeeded with other form fields empty. |
| Disable Google | Button disappeared; the existing session still worked. |
| Password fallback after disabling Google | Connected professor could still sign in and access the existing course. |
| Phone width (390px) | No horizontal overflow; Google cancellation returned to the usable login page. |
| Real Google handoff in a private tab | Google accepted the configured localhost client/callback and displayed its sign-in page. No real account was automated. |

Run the repeatable browser fixture after building the frontend:

```bash
cd frontend-dev && bun run build && cd ..
uv run python tests/google_login_browser_fixture.py
```

The fixture binds only to loopback, generates signing keys at runtime, uses a
temporary database, and exits without retaining test data. It is never imported
by FAIR. Open `http://localhost:8010/login`; the seeded password account is
`existing@example.edu`, password `fixture-password-123`. Select a scenario with
`POST /__test__/scenario` and JSON `{ "name": "existing" }` (see the fixture for
all names). `/__test__/invitation` opens the synthetic invitation URL.

## Automated coverage and fixes

Final local results: **58 Google-flow tests**, **118 existing auth/admission/
startup/release regressions**, and **57 PostgreSQL/migration/startup checks**
passed. The startup checks overlap between those last two groups. Frontend code
is unchanged from the PR's passing 108-test/typecheck/build run. Mintlify build
validation passed again after the rollout documentation update.

`tests/test_google_login.py` exercises real signed tokens through the HTTP routes.
Beyond the original signature, claims, state, expiry, replay and invitation cases,
coverage now includes provider outages/retry, multiple tabs, policy changes during
the redirect, allowlist subdomain boundaries, disabling Google with sessions in
use, password recovery for Google-only users, course/role retention, and refusing
an identity already linked to someone else.

Two new regression cases failed before the fixes and passed afterward:

- A password over bcrypt's UTF-8 byte limit raised a server error in account
  linking. It now returns the ordinary incorrect-password response, without
  truncating or accepting the oversized value.
- An operator could explicitly turn off Secure session cookies while enabling
  Google on HTTPS. Startup now rejects that configuration. HTTPS cookie flags
  and ordinary versus remembered lifetimes are tested through the callback.

## Rollout boundary

Read-only Railway configuration inspection confirmed neither staging nor
production has `FAIR_GOOGLE_CLIENT_ID` or `FAIR_GOOGLE_CLIENT_SECRET` configured.
Staging follows `nightly`; production follows `main`. Merging this PR into
`nightly` may trigger the existing staging auto-build, with Google still disabled.
It does not promote to production or publish the Google OAuth application.

The Google client used locally is not approved for production. Missing credentials
keep Google hidden, partial configuration fails startup, and password login stays
available. SSO-only access, school deprovisioning, Gmail-alias merging, disconnect,
Classroom grants, and Moodle connections remain outside this release.
