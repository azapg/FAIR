# Deploy FAIR on Railway

FAIR can run as one Railway service with SQLite and local artifact storage for
small research groups, demonstrations, and other single-node deployments. The
production image builds the React frontend and serves it from the same origin as
the API.

This profile is intentionally single-replica. Use PostgreSQL and S3-compatible
storage before adding replicas or treating the deployment as institutional
infrastructure.

## Railway resources

Configure one persistent service with:

- the repository `Dockerfile` as its build source;
- public HTTP networking on the Railway-provided port;
- a health check at `/health`;
- one persistent volume mounted at `/data`; and
- restart on failure, with a single replica.

The `/data` volume contains the SQLite database, uploaded artifacts, and locally
installed extension data. Back up the volume as one unit. Startup runs the
Alembic migration chain before serving requests, because Railway volumes are
available to the running service but not to pre-deploy commands.

## Required variables

```env
FAIR_DEPLOYMENT_MODE=COMMUNITY
FAIR_ADMISSION_MODE=invite_only
FAIR_AI_CONTROLS_ENABLED=false

FAIR_DATA_DIR=/data
DATABASE_URL=sqlite:////data/fair.db
FAIR_STORAGE_BACKEND=local
FAIR_AUTO_MIGRATE=1

FAIR_EMAIL_ENABLED=1
FAIR_ENFORCE_EMAIL_VERIFICATION=1
FAIR_RESEND_API_KEY=replace-in-railway
FAIR_EMAIL_SENDER=FAIR Platform <platform@example.org>

FAIR_BOOTSTRAP_ADMIN_EMAIL=admin@example.org
FAIR_BOOTSTRAP_ADMIN_NAME=FAIR Administrator

FAIR_BASE_URL=https://your-service.up.railway.app
FAIR_API_BASE_URL=https://your-service.up.railway.app
FAIR_CORS_ORIGINS=https://your-service.up.railway.app
FAIR_SESSION_COOKIE_SECURE=1

SECRET_KEY=replace-with-a-generated-secret
```

The Railway template generates `SECRET_KEY`. It prompts the deployer for the
Resend key, a sender whose exact domain is verified in Resend, and the initial
administrator identity. Never commit or place the Resend key in a template
default.

## First administrator

When `FAIR_BOOTSTRAP_ADMIN_EMAIL` is configured and the `users` table is empty,
startup creates exactly one verified administrator. It generates an unusable
random password and does not log or expose it. Use **Forgot password** with the
configured email address to establish the administrator password through Resend.

The bootstrap never promotes an existing account and never creates an additional
administrator after any user exists. Leaving the bootstrap variables in place is
therefore idempotent across restarts and deployments.

## Custom domain

Add the custom domain to the Railway service, then create the CNAME and ownership
TXT records that Railway provides at the authoritative DNS provider. After the
domain verifies, update these variables to the final HTTPS origin and redeploy:

```env
FAIR_BASE_URL=https://platform.example.org
FAIR_API_BASE_URL=https://platform.example.org
FAIR_CORS_ORIGINS=https://platform.example.org
```

The base URL controls password-reset, verification, and invitation links. The
Railway-provided domain remains a useful initial value until the custom domain is
ready.

## Email and invite-only registration

The Resend API key enables email automatically. `FAIR_EMAIL_ENABLED=1` and
`FAIR_ENFORCE_EMAIL_VERIFICATION=1` make ownership verification explicit. The
administrator can create email-bound, expiring, single-use invitations under
**Settings → Admin → Admission**.

The sender domain in `FAIR_EMAIL_SENDER` must exactly match a domain verified by
the Resend account associated with `FAIR_RESEND_API_KEY`.

## Operations

- Schedule Railway volume backups and test a restore before storing important
  coursework or research artifacts.
- Keep one application replica while SQLite and local storage are enabled.
- Download both `fair.db` and the `uploads` directory for an independent backup.
- Change `SECRET_KEY` only when intentionally invalidating all existing sessions
  and action links.
- Move to PostgreSQL and S3-compatible storage before multi-replica deployment.

FAIR includes `fair db migrate-sqlite-to-postgres` for a later controlled
database migration. Artifact bytes require a separate local-to-S3 migration.
