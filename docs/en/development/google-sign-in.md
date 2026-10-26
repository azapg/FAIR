---
title: Configure Google sign-in
description: OAuth configuration, rollout, recovery, and integration boundaries for developers and IT administrators
---

This page is for people who operate or develop a FAIR instance. For sign-in and
account-linking instructions, see [Google sign-in](/en/platform/integrations).

## Setup

1. Open **Google Auth Platform → Clients** in your Google Cloud project. For the
   FairGrade project, use [this page](https://console.cloud.google.com/auth/clients?project=fairgradeproject).
2. Configure the app's branding and audience if prompted. Use **External** to
   allow accounts outside one Google Workspace organization; in testing mode,
   add the accounts that will test the login.
3. Create an OAuth client with application type **Web application**. Add the exact
   callback for your backend to **Authorized redirect URIs**:

   | Environment | Callback example |
   | --- | --- |
   | Local frontend :3000, backend :8000 | `http://localhost:8000/api/auth/oidc/google/callback` |
   | One production hostname | `https://fair.example.edu/api/auth/oidc/google/callback` |
   | Separate API hostname | `https://api.fair.example.edu/api/auth/oidc/google/callback` |

4. Configure the server environment (keep the secret out of frontend config):

   ```dotenv
   FAIR_BASE_URL=https://fair.example.edu
   FAIR_API_BASE_URL=https://fair.example.edu
   FAIR_GOOGLE_CLIENT_ID=your-client.apps.googleusercontent.com
   FAIR_GOOGLE_CLIENT_SECRET=your-client-secret
   SECRET_KEY=your-existing-long-random-session-secret
   ```

5. Restart FAIR. **Continue with Google** appears on login and registration when
   both Google credentials are configured. With neither configured, it is hidden.
   Partial credentials or insecure origins fail startup with an actionable error.
   HTTP is supported only for localhost development. The frontend and API should
   be on the same site so browser cookie restrictions do not block sessions.

The Google project does not need Classroom or Drive enabled for login. FAIR asks
only for `openid email profile`, exchanges the code on the server, and discards
Google tokens after validating the identity. This flow uses a redirect, without
loading Google's browser SDK. Regular Google web-client creation is done in the
Cloud Console; `gcloud iam oauth-clients` serves a different Cloud OAuth use case,
and the former IAP OAuth administration commands are retired.
## Recovery and rollout

Password reset retains its current behavior: when email services are enabled, it
can establish a local password, including for a Google-created account. This
release does not enforce enterprise SSO-only access. Disable Google by removing
both Google credential variables; keep a password administrator for recovery.

### Existing accounts and email changes

A Google identity is linked to a FAIR account only after the user signs in to
FAIR, confirms their current password, and authenticates the Google account with
the same email. A matching email alone does not grant access to an existing account.
This also protects deployments where local accounts were marked verified while
email delivery was disabled.

Email comparison ignores case. Gmail dotted addresses, `+` aliases, and alternative
domains are not merged; use the address stored on the FAIR account for linking.
One Google account can be connected per FAIR account. Disconnecting, replacing a
Google account, and merging accounts are not included in this release.

After linking, the stable Google identity keeps pointing to the same FAIR user
even if the Google email changes. FAIR does not automatically update the local
email, role, or course access. Admission changes restrict new registrations;
they do not suspend existing users. School domain enforcement and deprovisioning
will need separate enterprise SSO policy.

### Validation before rollout

Test a new Google account, an existing password account connected from Profile,
login/logout, and a registration rejected by your current admission policy. In
invite-only mode, test the correct invitation email and an expired/revoked invite.
The backend tests exercise the real OIDC verifier with signed test tokens and
mocked Google HTTP endpoints. A live Google redirect still requires configured
credentials and an interactive consent test. Apply the same deployment login
rate limits to `/api/auth/oidc/*`. Configure access logs to omit callback query
strings, which contain short-lived authorization codes and state.

## Future school and LMS connections

External login identities are stored separately from FAIR users and institutional
data identifiers. A future school OIDC provider can reuse this boundary and FAIR
sessions. School hostnames, verified identity domains, organization membership,
and SSO enforcement will need explicit policy when that support is added; an
email domain alone does not grant school membership.

Google Classroom will use a separate **Connect Classroom** permission flow for
the specific course features enabled. Its encrypted authorization grants and
disconnect/reconnect lifecycle belong in a separate integration model. Disconnecting
course access should not disconnect Google login, and signing in with Google
does not grant course access.

For Moodle, launching FAIR from a course fits **LTI 1.3 / LTI Advantage**. General
course-data import or synchronization uses Moodle's enabled **Web Services**.
These integrations are not implemented yet. Existing organization-scoped
`ExternalIdentifier` mappings are for roster/course IDs, not login credentials.
