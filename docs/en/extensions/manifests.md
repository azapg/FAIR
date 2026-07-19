---
title: Extensions and manifests
description: Declare an Extension, its delivery mode, and its Capabilities.
---

An **Extension** is the code you connect to FAIR. Its **manifest** tells FAIR what the Extension is and what it can do.

## Manifest fields

| Field | Meaning |
| --- | --- |
| `manifestVersion` | Manifest contract version. Protocol 1 uses `"1"`. |
| `extensionId` | Stable lowercase identifier, such as `org.example.tutor`. |
| `displayName` | Name shown to people. |
| `version` | Extension release version. |
| `deliveryMode` | `webhook` or `runner`. Defaults to `webhook`. |
| `dispatchUrl` | HTTPS endpoint for webhook delivery. Not used by runners. |
| `healthUrl` | Optional HTTPS health endpoint. |
| `capabilities` | One or more Capability declarations. |

Use `webhook` when FAIR can reach your service. Use `runner` when your code runs on a laptop, lab computer, or private network.

## Minimal shape

```json
{
  "manifestVersion": "1",
  "extensionId": "org.example.assignment-agent",
  "displayName": "Assignment Agent",
  "version": "1.0.0",
  "deliveryMode": "runner",
  "capabilities": [
    {
      "capabilityId": "chat.assignment",
      "kind": "agent",
      "version": "1.0.0",
      "inputSchema": {"type": "object"},
      "outputSchema": {"type": "object"}
    }
  ]
}
```

See [Capabilities](/en/extensions/capabilities) for every available field.

<Note>
The canonical complete example is `specs/fixtures/extension-manifest.json` in the FAIR repository.
</Note>

<Warning>
TODO: Publish a stable manifest validator and initialization command in the standalone SDKs.
</Warning>
