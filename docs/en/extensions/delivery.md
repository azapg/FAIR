---
title: Delivery
description: Receive the same ExecutionCommand by webhook or local runner.
---

**Delivery** is how your Extension receives an `ExecutionCommand`.

| Mode | Choose it when... | Network requirement |
| --- | --- | --- |
| Webhook | your Extension is a reachable service | FAIR can call an HTTPS endpoint |
| Runner | code runs on a laptop or private network | outbound access to FAIR only |

Both modes receive the same command and use the same Execution APIs.

## Webhook

FAIR sends a signed HTTPS request to `dispatchUrl`. Verify the Ed25519 HTTP Message Signature before parsing or accepting the command.

Verification keys are available at:

```text
GET /api/v1/system/signing-keys
```

After verification, durably deduplicate `idempotencyKey`. Repeated delivery is normal.

## Runner

A runner long-polls for work:

```text
POST /api/v1/extensions/runner/commands/claim
POST /api/v1/extensions/runner/commands/{commandId}/ack
```

Claim returns `200` with a leased command or `204` when no command is ready. Record the command identity before acknowledging its exact `leaseId`.

An expired lease may be delivered again. Its `leaseId` changes; its logical command identity does not.

## Which credential goes where?

- Webhooks verify FAIR's request signature.
- Runners use the Installation credential only to claim and acknowledge commands.
- Both use the command's execution token for Events, Artifacts, and interactions.

See [Security](/en/extensions/security) before deploying either mode.

<Warning>
TODO: Publish supported webhook and runner adapters in the standalone Python and TypeScript SDKs.
</Warning>
