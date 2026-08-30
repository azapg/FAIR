# Railway infrastructure

`railway.ts` defines the FAIR service, one `/data` volume, one replica, the
`/health` deployment check, and non-secret deployment defaults.

Install dependencies, link the intended Railway project and environment, and
review the plan before applying it:

```bash
bun install
railway link
railway config plan
railway config apply
```

Values represented with `preserve()` must be supplied through the Railway
template or service variables. This keeps the Resend key, application secret,
administrator identity, sender, and public origins out of source control.

The infrastructure source follows `canary`, FAIR's deployment branch.

## Template composer contract

The public template must not inherit values from a maintainer deployment. Use
the following configuration when generating or updating it:

- GitHub source: `canary`;
- one generated HTTP domain routed to the container's port `8080`;
- health check `/health` with a 300-second timeout;
- one 5 GB volume mounted at `/data`; and
- one replica in a single region.

Required deployer inputs have no maintainer-specific default:

```env
FAIR_RESEND_API_KEY=
FAIR_EMAIL_SENDER=
FAIR_BOOTSTRAP_ADMIN_EMAIL=
FAIR_BOOTSTRAP_ADMIN_NAME=
```

Template-managed values are:

```env
DATABASE_URL=sqlite:////data/fair.db
FAIR_ADMISSION_MODE=invite_only
FAIR_AI_CONTROLS_ENABLED=false
FAIR_API_BASE_URL=https://${{ RAILWAY_PUBLIC_DOMAIN }}
FAIR_AUTO_MIGRATE=1
FAIR_BASE_URL=https://${{ RAILWAY_PUBLIC_DOMAIN }}
FAIR_CORS_ORIGINS=https://${{ RAILWAY_PUBLIC_DOMAIN }}
FAIR_DATA_DIR=/data
FAIR_DEPLOYMENT_MODE=COMMUNITY
FAIR_EMAIL_ENABLED=1
FAIR_ENFORCE_EMAIL_VERIFICATION=1
FAIR_SESSION_COOKIE_SECURE=1
FAIR_STORAGE_BACKEND=local
RAILWAY_HEALTHCHECK_TIMEOUT_SEC=300
SECRET_KEY=${{secret(64)}}
```

Before sharing the template URL, deploy it into a clean project and confirm the
generated domain, fresh volume, migrations, first-administrator reset flow,
invite-only policy, and restart persistence.
