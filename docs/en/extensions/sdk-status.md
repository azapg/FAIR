---
title: SDK status
description: See what works today and what is still missing.
---

The TypeScript SDK (`@fair/sdk`, in `sdk/typescript/`) is the supported way to
build an Extension. Start at [Build an Extension](/en/extensions/quickstart).

## Working today

End-to-end, with tests and a runnable demo in `extensions/core/`:

- `createExtension(...).start()` — runner transport, manifest self-sync on boot
- `agentCapability({ agent })` — hand over an AI SDK agent, unmodified
- `agentCapability({ run })` — yield strings, the SDK chunks and reports
- `functionCapability({ contract })` — implement a FAIR contract
- `flowStep(...)` — a pinnable node in a reproducible Flow
- `ctx.artifacts` — read version-pinned inputs, create provenance-stamped output
- bounded streaming chunks, token refresh, cancellation, deadlines
- exactly-one-terminal-outcome and idempotent retry, handled for you
- `fair ext bootstrap <id>` — issue a runner credential and allow effects

Verify a live instance with:

```bash
uv run python scripts/e2e_chat_demo.py --capability echo
uv run python scripts/e2e_chat_demo.py --capability tutor   # needs Ollama
uv run python scripts/e2e_flow_demo.py
```

## Not built yet

- **Python SDK.** `fair_platform.extension_sdk` remains an internal reference
  implementation, not a standalone package.
- **Contract registry as data.** `fair.rubric.generate@1` is currently
  recognised by id; contract files with declared UI placements, and the generic
  button that renders them, are still to come.
- **Installation scoping.** An Extension is enabled deployment-wide. The
  Registration / Installation / Grant split — which is what institutional batch
  installs and per-user community toggles need — is designed in
  `api-plan/extension-api-v2-proposal.md` but not implemented.
- **Portable Flow definitions.** Flow nodes still reference
  `capabilityDefinitionId` UUIDs, so a Flow cannot yet be exported, reviewed in
  a PR, or re-run on another FAIR instance. Publishing already pins versions;
  the definition needs `use: "ext@version#capability"` coordinates and explicit
  `in:` input mapping.
- **Managed binary Artifact upload.** Only `inlineJson` output is accepted.
- **Webhook delivery from the SDK.** The platform supports signed webhook
  dispatch; the SDK only speaks runner mode.
- **Resume / `ctx.ask()`.** The protocol supports interaction and resume; the
  SDK has no ergonomic wrapper yet.
- **Cross-extension tools.** Removed from Protocol 1 on purpose. See §8 of the
  spec for why, and what replaced it.

## Source of truth

| Source | Purpose |
| --- | --- |
| `specs/extension-execution-protocol.md` | normative Protocol 1 rules |
| `specs/fixtures/` | language-neutral contract examples |
| `sdk/typescript/` | the SDK |
| `extensions/core/` | FAIR's own extensions, built on the public SDK |
| `api-plan/extension-api-v2-proposal.md` | the design argument and what is deferred |

FAIR's built-in capabilities are ordinary Extensions with no privileged access.
If something they need is missing from the SDK, that is a bug in the SDK.
