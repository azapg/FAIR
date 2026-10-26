# Plan 009: Add Google login with a small foundation for school sign-in

> Executor: Read this entire plan before implementing. Preserve password login,
> admission rules, and existing browser/API sessions. Update the index when done.
> Drift check: `git diff --stat 83a15a5..HEAD -- src/fair_platform/backend frontend-dev/src tests pyproject.toml uv.lock .env.example docs/en/platform/integrations.md`.
> Compare the current-state excerpts if these paths changed; stop for material drift.

## Status

- Priority: P1
- Effort: M (authentication, migration, account linking, frontend, tests)
- Risk: HIGH (a new way to access existing accounts)
- Depends on: none; plan 003's cookie sessions are already implemented
- Category: direction
- Planned at: commit `83a15a5`, 2026-10-26
- Status: DONE; local Google sign-in confirmed by Allan, production not enabled

## Implementation results

Google login, explicit password-confirmed account linking, shared login/register
button, and English/Spanish messages are implemented. The identity model is
independent of organizations and LMS grants; no future SSO/LMS features were added.
The button remains hidden until both Google credentials are configured.

Validation: 162 targeted backend tests passed, including signed-token protocol
tests and existing auth/admission/startup/release behavior; 12 PostgreSQL 18 and
migration checks passed; all 108 frontend tests passed; frontend typecheck and
production build passed. Actual React login components were rendered with the
compiled application CSS and visually checked at 390px and 728px. That visual
uses an enabled-provider fixture, not live Google credentials. The complete
unrelated backend suite was not run.

Small implementation adjustments: transactions are atomically deleted and
returned when claimed, so no consumed timestamp is needed; identity coverage
lives alongside the protocol tests in `tests/test_google_login.py`; account
linking UI lives in its own small `google-account.tsx` component; two existing
system-config response expectations were updated for the additive provider field.

Allan configured a web OAuth client and subsequently confirmed real Google sign-in
on the separate local test instance. Credentials remain in private local runtime
configuration, outside the repository. The client is not approved for production;
no production credentials, consent settings, or deployed environment were changed.

Following Allan's documentation direction, the default English/Spanish welcome
and getting-started pages now address end users. Installation and technical
navigation live under a separate Developers & IT tab. User sign-in help stays in
`docs/en/platform/integrations.md`; exact callbacks, setup, recovery, and future
integration boundaries are in `docs/en/development/google-sign-in.md`.
The sections below retain the original implementation specification.

## Decision in plain language

Add **Continue with Google** to login and registration. Keep FAIR's current
accounts and sessions. Add a small record saying which external identity belongs
to which FAIR user, plus temporary records for the sign-in round trip.

Treat these as separate capabilities:

| Capability | Implement now | Later |
| --- | --- | --- |
| Sign in to FAIR | Google OpenID Connect (OIDC), identity permissions only | School OIDC connections; SAML if actually needed |
| Connect course data | Nothing yet | Google Classroom authorization; Moodle Web Services |
| Open FAIR from an LMS | Nothing yet | Moodle LTI 1.3 / LTI Advantage; investigate Classroom links or add-ons separately |

Google login is the first OIDC connection. It is not a Classroom integration.
Do not request Classroom/Drive permissions, offline access, or store Google
access/refresh tokens for login. No hosted authentication service is required.

## Why this matters

Users should enter FAIR without creating another password. The small external
identity boundary lets future school sign-in return to the same account/session
system. Keeping course permissions separate means a user can disconnect Classroom
without losing their Google login, and can connect Classroom after signing in
with a password or school SSO.

## Current state and conventions

- `src/fair_platform/backend/api/routers/auth.py:62-102` owns the `fair_session`
  cookie: HttpOnly, SameSite=Lax, path `/api`, Secure based on deployment settings.
  `create_access_token` and `_set_session_cookie` already support ordinary and
  remembered sessions. The frontend restores users through `/api/auth/me`.
- `auth.py:255-333` registers users, calls `authorize_registration`, and commits
  the user and invitation redemption together. Its new-user defaults include:

  ```python
  role=UserRole.user.value,
  password_hash=password_hash,
  is_verified=not get_email_enabled(),
  ```

  **Local `is_verified` is not necessarily proof of mailbox ownership.** Do not
  automatically join accounts with matching emails, even if that flag is true.
- `src/fair_platform/backend/data/models/user.py:32-49` already allows
  `password_hash=None` and has a unique normalized email. Keep both behaviors.
  `normalize_email_address` is the canonical comparison for local email matching.
- `src/fair_platform/backend/services/access_control.py:163-225` implements
  open/allowlist/invite-only registration. Existing users can still sign in after
  policy changes, as documented in `docs/en/platform/access-controls.md`.
- `src/fair_platform/backend/data/models/lms_organization.py:266-348` already has
  `ExternalIdentifier`, but it requires organization membership and also maps
  courses/cohorts. It is for institutional data matching, not login credentials.
  Global Google sign-in must work without an organization; do not repurpose it.
- `src/fair_platform/backend/api/routers/system.py` exposes public configuration
  through `/api/v1/system/config`; `frontend-dev/src/hooks/use-system-config.ts`
  types/loads it. Extend this response rather than adding a discovery endpoint.
- `frontend-dev/src/app/login/page.tsx` and `register/page.tsx` share
  `AuthPageShell`, shadcn `Button`, and English/Spanish translation keys.
  Registration reads `#invite=...`, retains it in component state, then clears
  the fragment. Preserve that behavior for Google registration.
- `frontend-dev/src/components/settings/sections/profile-section.tsx` has the
  existing password dialog. Add account linking here; follow its dialog/error
  patterns and `profile-section.test.tsx` tests.
- `frontend-dev/src/lib/api.ts` exports `getApiBaseUrl()` and sends cookies.
  Development uses frontend `:3000` / backend `:8000`; production uses `/api`.
- Backend conventions: SQLAlchemy `Mapped` models, UUID keys, named constraints,
  FastAPI dependencies, Pydantic schema aliases. `session_dependency` uses
  `autoflush=False`: explicitly flush before dependent inserts. Follow
  `data/models/lms_organization.py` and `api/schema/user.py` rather than adding
  another ORM or response-casing convention.
- Latest migration at this commit: `20261025_0037_clear_resubmitted_grades.py`.
  Add a new Alembic revision after it; never modify old revisions or startup
  database initialization.

## Scope

Only these paths may change (new files identified below):

- `pyproject.toml`, `uv.lock`, `.env.example`
- `src/fair_platform/backend/core/config.py`
- `src/fair_platform/backend/data/models/external_identity.py` (new),
  `data/models/__init__.py`, and one new `alembic/versions/*_google_login.py`
- `src/fair_platform/backend/services/oidc.py` (new),
  `services/external_identity.py` (new), `services/access_control.py`
- `src/fair_platform/backend/api/schema/external_identity.py` (new),
  `api/routers/oidc.py` (new), `api/routers/system.py`, `backend/main.py`
- `frontend-dev/src/components/auth/google-sign-in-button.tsx` (new),
  `src/app/login/page.tsx`, `src/app/register/page.tsx`,
  `src/hooks/use-system-config.ts`, `src/components/settings/sections/profile-section.tsx`,
  `src/i18n/locales/en.json`, `src/i18n/locales/es.json`
- `tests/test_google_login.py` (new), `tests/test_external_identity.py` (new),
  `tests/test_google_login_migration.py` (new), `tests/test_access_controls.py`,
  `tests/test_postgres_compat.py`, `tests/test_backend_startup_migrations.py`
- Frontend tests alongside the new button, login/register pages, and the existing
  `profile-section.test.tsx`; `docs/en/platform/integrations.md`; `plans/README.md`

Out of scope: auth/session replacement, SDK bearer changes, roles or automatic
organization enrollment, custom-domain hosting, enterprise SSO enforcement,
SAML, tenant administration UI, Classroom/Moodle sync, LMS launch routes,
disconnect/account-merge UI, unrelated settings improvements. Leave
`auth.py` unchanged; import its existing session/password helpers as needed.

Git: stay on the operator's working branch unless directed otherwise. Use a
conventional commit such as `feat(auth): add Google sign-in` when asked to commit.
Do not push or open a PR without instruction.

## Implementation steps

### 1. Add the identity and temporary transaction records

`ExternalIdentity`: UUID id; user FK; connection key (`google`); canonical issuer;
case-sensitive subject (up to 255 chars); created/last-login timestamps. Enforce
`UNIQUE(issuer, subject)` and `UNIQUE(user_id, connection_key)` for today's one
Google account per FAIR user. Index the user FK. No credential/token columns.

`OIDCTransaction`: random-state digest; browser-binding digest; connection key;
purpose (`login`/`link`); nonce; PKCE verifier; remember-me boolean; optional
target user FK for linking; optional invitation-token digest; expiry; consumed
timestamp. TTL: ten minutes. Store context server-side so invitation secrets,
link intent, and PKCE material do not travel through URLs or readable cookies.

Both are new tables; do not rewrite users or backfill guessed identities. Make
model imports available to Alembic and `Base.metadata.create_all` test fixtures.
Add migration tests from the previous head and against a populated users table.

**Verify:** `uv run pytest -q tests/test_google_login_migration.py tests/test_external_identity.py`
passes, including named uniqueness/FK checks and unchanged existing users.

### 2. Implement a thin OIDC service and round-trip handling

Add Authlib as the single direct protocol dependency and update the lockfile.
Use its asynchronous OAuth/OIDC client and verified ID-token parsing, not a
home-grown JWT verifier. Select a current compatible release at implementation
time; the researched references below describe the required APIs.

Keep one typed provider configuration with a small lookup keyed by connection
name. Only `google` is registered now: issuer `https://accounts.google.com`,
discovery `https://accounts.google.com/.well-known/openid-configuration`, scopes
`openid email profile`. Unknown connections fail closed. Request parameters
cannot supply an issuer, discovery URL, scopes, or redirect destination.

Configuration: `FAIR_GOOGLE_CLIENT_ID`, `FAIR_GOOGLE_CLIENT_SECRET`.
Neither set means disabled; partial configuration is an actionable startup error.
Enabling Google requires an explicitly configured strong session secret even in
community mode. Derive the fixed callback from the explicitly configured
`FAIR_API_BASE_URL`, and the frontend destination from `FAIR_BASE_URL`; require
HTTPS except localhost development. Do not derive either from incoming Host or
Forwarded headers. Validate once and expose only enabled provider keys/labels
under `authentication.providers` in public system config.

Use Authlib's `create_authorization_url`, `fetch_access_token`, and
`parse_id_token` with the saved state/nonce/PKCE context. This explicit flow
allows FAIR's transaction table to own temporary state; no new session
middleware or generic cache adapter is necessary. Configure PKCE S256. Validate
signature, expected issuer, audience/authorized party, time claims, nonce,
nonempty subject, valid email, and verified email. If accepting Google's legacy
issuer spelling, validate it explicitly before canonicalizing it; never
normalize arbitrary issuers into trust. Do not trust unsigned `userinfo` data.

Set a separate random, HttpOnly, SameSite=Lax, host-only browser-binding cookie
at `/api/auth/oidc`, Secure outside localhost, TTL ten minutes. Compare its digest
as well as the state digest on callback. Atomically claim an unexpired,
unconsumed transaction with an update predicate and require exactly one row;
commit the claim before token exchange so concurrent callbacks cannot both
proceed. Do not hold a database transaction open across provider HTTP calls.
One pending login per browser is sufficient; a later start replaces the old
cookie. Another tab's old callback fails safely.

Use bounded HTTP timeouts. On success or a validated failure, delete temporary
proof material and clear the binding cookie. Opportunistically delete expired
records at starts so no scheduler is required. Wrong-browser requests must not
consume a valid transaction. Log error categories only; suppress/redact callback
codes, state, tokens, invitation data, and provider error descriptions.

**Verify:** `uv run pytest -q tests/test_google_login.py -k 'configuration or protocol or transaction'`
passes with mocked discovery/token/JWKS HTTP responses and real signed test ID
tokens. Include protocol failures, not just a stub returning trusted claims.

### 3. Resolve accounts without bypassing admission or joining by email

Resolution order is intentional:

1. A known `(issuer, subject)` logs into that FAIR user. Keep its id, local name,
   email, roles, enrollments, and settings unchanged if Google profile data changes.
   Registration admission is not rerun. Provider claims do not grant roles.
2. An unknown identity whose normalized email already belongs to a FAIR account
   must not attach itself or create another user. Return an `account_link_required`
   result: sign in normally and connect Google in Profile.
3. For a genuinely new email, rerun current admission policy at callback, then
   atomically insert the user (`password_hash=None`, role `user`, verified from
   validated Google email), identity, and any invitation redemption. Use the
   claimed Google name or email fallback. Roll back all three on any failure.

Preserve invite secrecy across redirects: store only its digest. Refactor the
existing `authorize_registration` into a public raw-token wrapper plus a shared
internal digest-based checker, retaining length limits, hashing, email binding,
expiry, revocation, and mode semantics. Only server-owned transaction data can
call the digest variant; never accept an invite digest from public JSON.
Recheck at callback because an administrator can revoke/change policy while the
user is at Google. Conditional invitation redemption must also prevent concurrent
reuse on SQLite, where `FOR UPDATE` alone is insufficient.

For linking, require a logged-in FAIR user, a fresh correct current password, an
explicit POST with a trusted frontend Origin, and Google email matching that
user's normalized email. Bind the target user to the server transaction and
revalidate the same authenticated user on callback. Reject expired/switched
sessions, a Google identity owned by another user, and attempts to replace an
existing linked identity. A completed link may mark that same local email verified.
Do not silently switch the current user. Never merge users or transfer identities.

Use database uniqueness as the authority for races. On a duplicate callback or
concurrent signup, issue no session for the losing request; return a clean retry
result without leaking exception detail. Use FAIR's existing session helpers
after the successful account transaction commits. Google tokens are discarded.

**Verify:** `uv run pytest -q tests/test_external_identity.py tests/test_google_login.py tests/test_access_controls.py tests/test_auth_integration.py`
passes, including email collision with a local account created while email was
disabled, invite revocation during redirect, concurrent redemption/identity claims,
and existing cookie/bearer behavior.

### 4. Add the endpoints and a minimal UI

Mount `api/routers/oidc.py` at `/api/auth/oidc` in `main.py`.

| Endpoint | Contract |
| --- | --- |
| `POST /api/auth/oidc/google/start` | Public JSON `{inviteToken?, rememberMe?}`. Sets binding cookie, returns `{authorizationUrl}`; login/signup intent only. Validate Origin. |
| `GET /api/auth/oidc/google/callback` | Browser redirect from Google. Claims transaction, validates tokens, resolves account, sets FAIR session, sends 303 to fixed frontend `/`. |
| `GET /api/auth/oidc/identities` | Authenticated; return `hasPassword` and safe linked-provider labels. Never return subjects, credentials, or raw claims. |
| `POST /api/auth/oidc/google/link` | Authenticated JSON `{currentPassword}` plus trusted Origin. Fresh password verification, creates a link transaction, returns `{authorizationUrl}`. |

POST responses use the repo's existing schema alias conventions. No user-supplied
`next`/return URL in v1. On callback failure redirect to fixed `/login` with a
small allowlisted error code (`cancelled`, `account_link_required`,
`registration_not_permitted`, `try_again`); no email, raw provider message, or
credential in the redirect. Linking errors can use the same login notification
while preserving the currently signed-in account. Add no new React callback
route: a full-page return lets the existing AuthProvider reload `/auth/me`.

One shared `GoogleSignInButton` calls the start endpoint using `api`, then
`window.location.assign(authorizationUrl)`. Its `type="button"` must not submit
the password form; email/password fields must not gate Google login. Registration
passes the existing invitation state, and only requires an invitation when the
current mode requires it. Login passes the remember-me preference. Handle double
clicks and request failures, with English/Spanish copy. Hide Google when disabled
or config loading fails. Do not expose provider secrets in frontend environment.

In Profile, show `Connect Google` with a current-password dialog for unlinked
password accounts, or a compact `Google connected` label. For Google-only users,
hide the unusable change-password action. Keep current password-reset recovery
behavior unchanged in this phase and document it; SSO-only enforcement later
must deliberately cover password reset, verification, and all login paths.

Before implementing UI placement, use the available UI/shadcn skills and show
Allan two small labeled previews: A, Google above the existing form (recommended);
B, Google below it. Retain the current shell/typography; no new login design.
Use Google's permitted button branding. Selecting layout does not block backend
work. Deliver visual evidence after implementation using the host's HTML preview
and render tools; never claim that an unimplemented mockup is a working login.

**Verify:** from `frontend-dev`, run `bun x tsc --noEmit`,
`bun run test --maxWorkers=2`, and `bun run build`, all exit 0. Tests cover provider
visibility, independent form validity, invitations, remember-me, failure/retry,
link status/password prompt, and Google-only password controls. Use
`src/components/settings/sections/profile-section.test.tsx` as the testing pattern.

### 5. Document setup and validate both database profiles

Add disabled-by-default Google configuration examples to `.env.example` and fill
in the currently empty `docs/en/platform/integrations.md`. Document Google Cloud
OAuth web-client setup, consent audience, test users, client credentials, public
frontend/API origins, and exact callback URLs:

- Local: `http://localhost:8000/api/auth/oidc/google/callback`
- Same-origin production example: `https://fair.example.edu/api/auth/oidc/google/callback`
- Split-origin example: `https://api.fair.example.edu/api/auth/oidc/google/callback`

Callback URLs must be registered exactly. Scope examples contain only
`openid email profile`. Each self-hosted deployment supplies its own credentials.
Test local and production-style origins, HTTPS cookie flags, login persistence,
logout, existing-user linking, first Google signup, and restricted signup denial.

**Verify:** run the backend and frontend gates below. Use temporary database
fixtures, never the operator's live database. PostgreSQL tests must run in CI with
`POSTGRES_TEST_STRICT=1` and a configured disposable test server, including the new
table constraints, migration, and concurrent transaction claims. A skip is not
PostgreSQL verification. Record actual results in the implementation handoff.

## Commands and evidence

These commands are established by `pyproject.toml`, `.github/workflows/test.yml`,
and `.github/workflows/frontend.yml`. At planning time this worktree has `uv` and
`bun` but no `.venv` or `frontend-dev/node_modules`. No app tests were run for this
read-only planning task. Executors install dependencies before the gates.

| Purpose | Command | Success |
| --- | --- | --- |
| Backend dependencies | `uv sync --extra test` (after adding Authlib and resolving lock) | exit 0 |
| Frontend dependencies | `cd frontend-dev && bun install --frozen-lockfile` | exit 0 |
| New auth + regressions | `uv run pytest -q tests/test_google_login.py tests/test_external_identity.py tests/test_google_login_migration.py tests/test_auth_integration.py tests/test_access_controls.py tests/test_bootstrap_admin.py tests/test_backend_startup_migrations.py` | all pass |
| Migration regressions | `uv run pytest -q tests/test_migration_rehearsal_files.py tests/test_postgres_compat.py` | all applicable pass; PostgreSQL skips disclosed |
| Backend CI | `uv run pytest` | all pass, or clearly separate confirmed pre-existing failures |
| Frontend CI | In `frontend-dev`: `bun x tsc --noEmit`, `bun run test --maxWorkers=2`, `bun run build` | each exits 0 |
| Review scope | `git diff --check` and `git status --short` | no whitespace errors; only scoped changes |

Use existing `tests/conftest.py` temporary DB/client fixtures. New tests must cover:
missing/partial credentials; unknown connection; fixed origin/callback behavior;
CSRF Origin failure; cancellation; missing/wrong state or cookie; expiry/replay;
PKCE/nonce; tampered signature, issuer, audience, authorized party, time claims;
missing/unverified email; stable subject after email change; email collision;
successful and rejected linking; no password for new Google users; admission in
all three modes; invite wrong-email/expiry/revocation/reuse; identity races;
cookie attributes, remember-me, `/auth/me`, and no credentials in response URLs.

## Future additions: preserve these boundaries, do not build them now

**Enterprise SSO and custom domains.** Two distinct meanings matter: the school's
FAIR hostname and its identity/email domain. A custom hostname needs hosting/TLS,
trusted host routing, and exact callback registration; it grants no membership.
For a dedicated deployment, add an operator-configured OIDC connection. For
multiple schools sharing one deployment, add organization-scoped auth connections,
verified domains, trusted tenant resolution and login enforcement, and membership
provisioning rules. Reuse today's external identity resolver and FAIR sessions.
An email suffix is a routing hint, not proof of school membership. For Google
Workspace restrictions, enforce the validated `hd` claim, not a requested `hd`
parameter. Design provider-linking and session revocation with actual enterprise
policy before enabling SSO-only access. SAML can be a separate adapter or broker
if a customer needs it; an OIDC client does not itself implement SAML.

**Google Classroom.** A separate authenticated `Connect Classroom` flow asks only
for permissions needed by the first actual feature, incrementally and separately
for teachers/students where relevant. Add a `ConnectedAccount`/authorization-grant
model then: FAIR user, provider account identity, granted scopes, encrypted token
material, expiry, refresh/revocation state, and disconnect/reconnect handling.
Do not store secrets in `User.settings`, `ExternalIdentity`, or
`ExternalIdentifier.attributes`. Bind each grant to the current FAIR user; the
chosen Classroom Google account need not be the login account, but must never
silently relink it. Reuse OAuth mechanics, not login admission or identity-linking
side effects. Account for school admin approval and Google's scope verification
before promising rollout. A Classroom add-on is a separate distribution/UI choice.

**Moodle.** For opening FAIR from Moodle with class/user context and possibly
grades, prefer registering FAIR as an LTI 1.3 tool; plan LTI Advantage services
only as required. LTI launch identities must be scoped to the trusted platform
registration/deployment, with validated launch claims; they cannot be joined by
email alone. Embedding and form-POST launches need a dedicated cookie/launch
design, not a blanket weakening of FAIR's session-cookie settings. For importing
or syncing arbitrary Moodle course data, investigate that school's enabled Web
Services and permissions. Moodle OAuth login is not a universal course-data API.
Use the existing organization-scoped `ExternalIdentifier` for course/roster data
mappings, with distinct system keys for different Moodle instances.

## Done criteria

- [ ] Both new tables migrate cleanly on SQLite and PostgreSQL; existing user IDs,
  roles, courses, password logins, and SDK bearer authentication are preserved.
- [ ] All applicable verification gates above pass; skipped/unavailable checks
  are explicitly disclosed with their reason.
- [ ] Provider-disabled deployments retain the current UI and behavior.
- [ ] New Google users have no generated/fake password and pass current admission.
- [ ] Known identities return to the same account; matching email cannot attach
  an identity without explicit authenticated/password-verified linking.
- [ ] Real protocol-validation tests reject forged tokens and invalid round trips.
- [ ] A configured Google test-client smoke test confirms the redirect, Google
  consent, return, cookie session, account linking, and logout. If credentials are
  unavailable, report mocked verification and the outstanding live smoke test.
- [ ] Google login requests no Classroom/Drive scopes or offline access and
  persists no provider access/refresh tokens.
- [ ] UI option selected before implementation; final visual proof supplied.
- [ ] Setup documentation and the plan index reflect actual completion state.

## STOP conditions and maintenance

Stop for material source drift, a need to change out-of-scope session/SDK APIs,
unclear account ownership, or two failed attempts at a verification gate. Report
the exact blocker rather than weakening claim/state checks or admission policy.
Missing real Google credentials blocks the live smoke test, not offline work;
use the host's secret-request tool for credentials if/when that test is requested.

Reviewers should scrutinize email collisions, callback/browser binding, atomic
claims, invitation redemption on SQLite, and the point where a FAIR session is
issued. Do not convert these into a provider plugin system. The first new school
connection is the right time to extend provider configuration and policy.

## Primary references checked during planning

- [Google OIDC](https://developers.google.com/identity/openid-connect/openid-connect):
  code flow, stable subject IDs, claim validation, nonce/state, Workspace `hd`.
- [Authlib Starlette client](https://docs.authlib.org/en/v1.6.5/client/starlette.html)
  and [web OAuth clients](https://docs.authlib.org/en/v1.6.5/client/frameworks.html):
  asynchronous integration, PKCE, token parsing, login without token persistence.
- [Authlib async implementation](https://github.com/authlib/authlib/blob/v1.6.5/authlib/integrations/base_client/async_app.py):
  explicit authorization URL creation/token exchange for server-owned state.
- [Classroom authorization](https://developers.google.com/workspace/classroom/guides/auth):
  separate scopes, least privilege, verification considerations.
- [Moodle LTI tools](https://docs.moodle.org/en/External_tool) and
  [Moodle Web Services](https://moodledev.io/docs/5.0/apis/subsystems/external):
  in-course launches and external data APIs are separate integration choices.

Not audited: unrelated application behavior, live Google Cloud settings, any
particular school's SSO/Moodle configuration, deployment DNS/TLS, and production
provider consent or permissions. Future sections are design boundaries, not
implemented or validated integrations.
