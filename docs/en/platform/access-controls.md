---
title: Admission and AI cost controls
description: Configure registration policy and weighted AI execution credits for a shared FAIR deployment
---

FAIR treats admission and AI access as separate decisions. Admitting an account does not grant it AI spending authority, and course roles or extension grants do not replace either control.

The compatibility defaults are **open registration** and **AI controls disabled**. Existing accounts can continue to sign in when an operator changes the registration policy.

## Bootstrap an administrator

Create the first verified administrator from the deployment environment rather than opening public registration:

```bash
fair users create-admin admin@example.edu --name "FAIR Administrator"
```

The command prompts for a password and bypasses only the public registration policy. Run database migrations before using the command.

## Registration admission

An administrator can choose a mode under **Settings → Admin → Admission**:

| Mode | Registration behavior |
|---|---|
| Open | Any valid email address may register. |
| Approved emails | The normalized address must match an approved individual address or its exact domain must be approved. Subdomains are not implicit wildcards. |
| Invite only | Registration requires an unexpired, unrevoked, single-use token bound to the same normalized email address. |

Administrators can add and remove exact email or domain rules and create or revoke invitations. The invitation URL is shown only when it is created. FAIR stores a hash of the token, not the plaintext token, and places the token in the URL fragment so it is not sent in the initial HTTP request. Registration with an invitation does not mark the email as verified; ordinary verification policy still applies.

Use `FAIR_ADMISSION_MODE=open|allowlist|invite_only` when deployment configuration should be authoritative. When present, this value overrides the stored setting and locks the mode selector in the admin UI. Rules and invitations remain database-managed.

An allowlist matches the address a registrant supplies; it is not proof that the registrant owns that mailbox. Internet-facing allowlist deployments should configure a mail provider and set both `FAIR_EMAIL_ENABLED=1` and `FAIR_ENFORCE_EMAIL_VERIFICATION=1`. Without enforced verification, an attacker can self-assert an address in an approved domain.

## AI entitlements and weighted credits

Enable AI controls only after completing both setup steps:

1. Classify every installed capability as **unmetered** or **AI**, and assign a positive integer credit cost to each AI capability.
2. Give each intended user a **disabled**, **limited**, or **unlimited** AI entitlement. A limited entitlement requires a monthly credit limit.

When controls are enabled, FAIR reserves a capability's configured credits atomically before creating its dispatch. Chat agents, functions, and each Flow step use this central execution path. A request is denied before provider work begins when the capability is unclassified, the user lacks an entitlement, or the monthly limit would be exceeded. Monthly counters reset on the first day of the month in UTC.

Credits are operator-defined weights, not provider tokens, currency, invoices, or a guaranteed dollar ceiling. A successful reservation is retained as an immutable usage charge even if the downstream provider later fails; refunds and provider-price reconciliation are outside the first version. Operators should choose conservative weights and reconcile the audit log with provider billing.

`FAIR_AI_CONTROLS_ENABLED=true|false` overrides the stored enforcement switch and locks it in the admin UI. If it is set to `true` while a capability is unclassified, that capability fails closed. Omitting it leaves the switch database-managed and disabled by default.

## Recommended rollout

1. Back up the database and run the Alembic migration. It stops with an actionable error if existing emails collapse to the same normalized identity; FAIR never merges or deletes those users automatically.
2. Create or confirm an administrator and keep registration open during validation.
3. Add admission rules or invitations, test a new registration, then change the admission mode.
4. Classify all capabilities and grant small test entitlements while AI controls remain disabled.
5. Enable AI controls, exercise chat, function, and Flow paths, and review **Settings → Admin → AI controls** usage records.
6. Raise user limits deliberately after comparing weighted credits with real provider usage.

For rollback, set `FAIR_ADMISSION_MODE=open` and `FAIR_AI_CONTROLS_ENABLED=false`, or restore those stored values through the admin UI when environment overrides are absent. This preserves rules, invitations, entitlements, and the usage audit for later reuse.

## Security and operations

- Keep invitation links confidential and short-lived. Revoke unused links when recipients change.
- Enforce email verification when admission depends on an approved address or domain. Possession of an invite link is the credential in invite-only mode, so protect it like a password-reset link.
- Put internet-facing registration and login endpoints behind reverse-proxy or WAF rate limits and monitoring. IP allowlisting is not part of FAIR's application policy and is usually too coarse for a general deployment.
- Use HTTPS, a strong `SECRET_KEY`, controlled administrator accounts, backups, and database least privilege.
- Treat the UI as guidance only. The API enforces administrator authorization, admission rules, entitlements, and credit reservation server-side.
- Registration admission does not suspend an existing account, assign course membership, grant extension effects, or prove ownership of an email address.

The former FAIR public community instance is currently offline, and its future availability is not guaranteed. These controls are deployment-neutral and can be used by any FAIR operator.
