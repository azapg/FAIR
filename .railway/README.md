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

The source branch is temporary while the Railway template is validated. Point it
to a stable merged branch or release before publishing the deployment button.
