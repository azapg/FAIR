# Implementation plans

| Plan | Status | Depends on | Summary |
| --- | --- | --- | --- |
| 001 | DONE | — | Fix course hook order |
| 002 | DONE | — | Fix chat hook order |
| 003 | DONE | — | HttpOnly browser session and Axios hardening |
| 006 | DONE | — | Serialize settings updates |
| 004 | DONE | 002 | Stabilize Execution streaming and renders |
| 005 | DONE | — | Add route bundle boundaries |
| 007 | DONE | 002, 004 | Accessibility baseline |
| 008 | DONE | 002, 004, 005 | Canonical chat and domain architecture |
| [009](009-google-login-and-federated-identity.md) | DONE | — | Google login, account linking, and separate user/admin docs |

Execution gates completed in order: correctness/security, performance, accessibility, then architecture consolidation. Every plan was implemented against 4210a60 and validated together.

The original completed execution gates above refer to plans 001–008. Plan 009 was
written against `83a15a5` on 2026-10-26 and subsequently implemented. Its checks:
162 backend auth/admission/startup/release tests, 12 PostgreSQL/migration tests,
108 frontend tests, frontend typecheck and production build. The login UI was
visually checked at phone and desktop widths using the actual React components.
Allan subsequently confirmed interactive Google sign-in on the local test instance.
The OAuth client is not approved for production, and no deployment was performed.
User help lives in `docs/en/platform/integrations.md`; setup and recovery are in
`docs/en/development/google-sign-in.md` under the separate Developers & IT tab.

Plan 009 covers Google login now. Enterprise SSO, Classroom permissions, and
Moodle launches/sync remain future work with explicit boundaries in that plan.
