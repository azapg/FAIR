---
title: Security
description: Understand Extension identity, execution tokens, scopes, and signatures.
---

FAIR gives each credential one job.

| Credential | Job | Educational data access |
| --- | --- | --- |
| User session | use FAIR as a person | based on the user's role |
| Installation credential | claim and acknowledge runner commands | none |
| Execution token | act for one Execution | only listed scopes and resources |
| FAIR signing key | prove a webhook command came from FAIR | not applicable |

FAIR never forwards a user session token to an Extension.

## Execution token

The command contains a short-lived token bound to:

- one Execution and root Execution;
- one Installation and Capability definition;
- the initiating user and Extension actor;
- explicit scopes;
- typed course, assignment, submission, and Artifact IDs.

FAIR checks those bindings on every API call. Disabling an Installation or terminating an Execution invalidates its authority.

## Scopes and effects

**Scopes** control which Execution APIs a token may call. **Declared effects** describe consequential behavior, such as writing feedback. Contextual Grants decide whether those effects are allowed.

## Webhook signatures

Webhook receivers must verify the request method, target URI, body digest, content type, key, nonce, and freshness window before accepting a command.

## Safe defaults

- Keep provider credentials inside the Extension.
- Never log execution tokens or commit them as fixtures.
- Deduplicate before external effects.
- Treat command input as untrusted even after signature verification.
- Keep consequential decisions, including final grades, in FAIR's authorized review path.
