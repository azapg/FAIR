# FAIR Extension Execution Protocol 1

Status: **implemented Phase 3 contract**

This document is normative for Protocol 1. The public reference starts in
`docs/en/extensions/overview.md`; the Pydantic wire contracts
are in `fair_platform.extension_sdk.contracts`.

The protocol is the only external execution boundary between FAIR and custom
behavior. Agents, tools, graders, actions, and Flow steps receive the same
`ExecutionCommand`, append to the same Execution event log, and use the same
authorization and Artifact APIs.

## 1. Consumer mental model

An Extension author needs five concepts:

1. A **Capability** describes versioned callable behavior.
2. An **ExecutionCommand** asks one exact capability version to start, resume,
   or cancel one Execution.
3. The command's **execution token** is the complete temporary authority for
   that Execution. FAIR never forwards a user session token.
4. The Extension reports durable **Events** and may create **Artifacts** through
   the command's `platformUrl`.
5. The Extension produces exactly one terminal outcome.

Queue rows, leases, retries, projection tables, and SSE fan-out are platform
machinery. They MUST NOT become required concepts in product or Extension APIs.

## 2. Protocol and schema rules

- `protocolVersion` MUST be the string `"1"`.
- Wire JSON MUST use camel-case field aliases.
- FAIR protocol envelopes MUST reject unknown fields.
- Capability input and output schemas MUST be valid JSON Schema Draft 2020-12.
- The exact installed CapabilityDefinition ID, semantic capability ID, and
  version MUST be frozen onto an Execution before dispatch.
- FAIR MUST validate initial input and successful output against the schemas in
  that frozen manifest snapshot.
- URLs supplied by an installation for dispatch and health checks MUST use
  HTTPS. Local development behind NAT SHOULD use runner delivery.

The canonical fixture is `specs/fixtures/execution-command.json`. Its token is
test-only redacted text and MUST NOT be interpreted as a working credential.

## 3. One command, two delivery adapters

The serialized `ExecutionCommand` MUST be independent of delivery mode.

### 3.1 Command identity

- `commandId` identifies one durable dispatch record.
- `idempotencyKey` identifies one logical start, resume, or cancel command.
- Delivery is at least once. The consumer MUST durably deduplicate the logical
  identity before effects.
- A redelivery MUST preserve `commandId`, `idempotencyKey`, Execution identity,
  and Capability pin. A new runner lease receives a new `leaseId` only.
- `issuedAt` and the short command expiry MAY be regenerated for a later
  delivery attempt. They do not change the logical command.
- A platform idempotency key MUST identify the complete logical request.
  Reusing it with different content or a different Capability pin MUST return
  `409`.

### 3.2 Webhook adapter

FAIR sends the exact command bytes to the installed HTTPS dispatch URL. The
request MUST contain an Ed25519 HTTP Message Signature using the FAIR profile
implemented in `fair_platform.extension_sdk.signatures`.

The signature covers:

```text
"@method" "@target-uri" "content-digest" "content-type"
```

The signature parameters MUST contain `created`, `expires`, `nonce`, `keyid`,
`alg="ed25519"`, and `tag="fair-execution-command"`. The validity window MUST
be at most 300 seconds. The receiver MUST verify body digest, exact method,
exact target URI, content type, freshness, and public key before accepting the
command. Keys are discovered from `GET /api/v1/system/signing-keys` as Ed25519
JWKs.

The nonce identifies a signed delivery. The stable command idempotency key,
not the nonce, remains the authoritative defense against repeated effects.

Community mode derives a deterministic development signing key so local
commands survive restarts. Enterprise startup MUST fail unless
`FAIR_DISPATCH_SIGNING_PRIVATE_KEY` contains an independently generated,
base64url-encoded 32-byte Ed25519 private seed.

### 3.3 Runner adapter

An outbound runner authenticates with an installation credential scoped only
to `runner:commands`.

```text
POST /api/v1/extensions/runner/commands/claim
POST /api/v1/extensions/runner/commands/{commandId}/ack
```

Claim input is `{runnerId, waitSeconds, leaseSeconds}` where `waitSeconds` is
0-30 and `leaseSeconds` is 10-300. `200` returns a `RunnerCommandLease`; `204`
means no work. Acknowledgement MUST carry the exact `leaseId`. Repeating an ack
for the same already-acknowledged lease is harmless. A wrong or expired lease
returns a conflict. Webhook delivery workers use the same lease fencing
internally: a worker whose lease expired or was reclaimed MUST NOT mark the
new lease delivered or failed.

The installation credential MUST NOT authorize event, Artifact, interaction,
or tool APIs. Those calls use only the command's execution token.

## 4. Execution authority

The execution token is a typed JWT with:

- header type `fair-execution+jwt`;
- purpose `execution_delegation`;
- audience `fair-extension-api`;
- issuer `{FAIR_API_BASE_URL}/api/v1`;
- initiating user in `sub`;
- installation actor in `act.sub`;
- JTI, issue time, and expiry;
- Execution, root Execution, installation, and CapabilityDefinition IDs;
- explicit scopes;
- typed course, assignment, submission, and Artifact resource claims.

FAIR MUST check token type, purpose, issuer, audience, signature, expiry, actor,
installation enabled state, exact Execution and capability bindings, requested
scope, and route resource on every use.

The base execution scope is `executions:events`. Capability-requested scopes
are added to the command. A token MAY refresh before expiry at:

```text
POST /api/v1/executions/{executionId}/authorization/refresh
```

Refresh MUST preserve the original scopes and resource binding. It MUST fail
after cancellation is requested, after terminal state, after installation
disablement, or after token expiry.

FAIR MUST NOT issue fresh execution authority or build a new command for a
terminal Execution.

Terminal state revokes the token on every route except an exact retry to event
ingest. That exception can only acknowledge an event whose producer identity
already exists; new terminal-state events receive `401`.

## 5. Event ingestion and idempotency

```text
POST /api/v1/executions/{executionId}/events/ingest
```

The body is `ExecutionEventBatch`, contract `fair.execution-event.v1`, with
1-100 durable events. FAIR does not persist ephemeral events in this protocol.

Each producer event has a `(producerSource, producerEventId)` identity. FAIR:

1. validates that source against the token's installation;
2. returns the existing accepted event for an identical retry;
3. returns `409` if that identity was already accepted with different content;
4. locks the Execution row;
5. rejects a new event for a terminal Execution;
6. assigns the next server sequence;
7. appends and projects in one transaction.

The Execution row lock is the lifecycle and event-order serialization boundary
on PostgreSQL. The event log is authoritative. Projection rebuild deletes
derived message and snapshot state, resets the Execution projection fields,
and replays the durable sequence.

### 5.1 Standard event semantics

Lifecycle events:

- `execution.started`
- `execution.waiting`
- `execution.completed`
- `execution.failed`
- `execution.cancelled`
- platform-authored `execution.expired`

Message events:

- `message.started`
- `message.part.created`
- `message.delta`
- `message.completed`
- `message.failed`
- `message.cancelled`

Interaction and lineage events:

- `interaction.requested`
- platform-authored `interaction.resolved`
- `artifact.created`
- platform-authored `tool.invocation.created`

FAIR MUST validate the semantics of standard events before projection.
Extension messages MUST use `authorType="extension"`; all message, part,
Thread, and Turn IDs MUST belong to the current Execution. Extensions MUST NOT
emit `interaction.resolved`.

Custom events are allowed for research observations. They MUST have a stable
`schemaUri` and remain subject to strict envelope, producer, Execution,
visibility, durability, ordering, and terminal-state rules. FAIR does not infer
product lifecycle from a custom event.

### 5.2 Streaming chunks

Extensions SHOULD buffer provider tokens into bounded chunks. They MUST NOT
assume one upstream model token equals one durable HTTP event. The internal
reference reporter flushes at 100 ms or 2,048 characters by default and MUST
flush buffered text before a terminal event.

`message.delta` appends text only to a part owned by the message and Execution.
Durable sequence, not provider token position, is the resume cursor.

## 6. Lifecycle

Allowed transitions are:

```text
queued  -> running | waiting | terminal
running -> waiting | terminal
waiting -> running | terminal
```

Terminal is exactly one of `completed`, `failed`, `cancelled`, or `expired`.
No terminal state transitions to another state. Stream closure, webhook status,
runner death, and process exit MUST NOT imply a terminal result.

The same Execution-row lock used for event sequencing ensures two competing
terminal transactions cannot both commit. The losing event is rejected.

### 6.1 Cancellation

User cancellation is idempotent. If the capability declares
`supportsCancellation`, FAIR enqueues one durable `cancel` command. Otherwise
FAIR records `execution.cancelled` itself. After a cancellation request, the
Extension may only report `execution.cancelled` or `execution.failed`; Artifact
creation and late success are rejected.

### 6.2 Deadline expiry

Commands and tokens cannot outlive the Execution deadline. The dispatch workers
run a deadline watchdog. It locks each overdue non-terminal Execution and emits
one platform-authored `execution.expired` event. Repeated watchdog runs are
idempotent.

### 6.3 Pause and resume

Only a capability with `supportsResume=true` may emit `interaction.requested`.
FAIR projects one user-owned InteractionRequest and moves the Execution to
waiting. The authenticated user resolves or declines it. FAIR records
`interaction.resolved` and enqueues one idempotent `resume` command containing
the result. An Extension cannot resolve its own request.

## 7. Artifacts

Input access MUST be represented by `ExecutionInputArtifact`, not an arbitrary
path or resource ID embedded only in JSON. FAIR freezes assignment- and
submission-linked Artifacts before dispatch. Child tool Executions inherit the
parent's frozen inputs. Before freezing, FAIR MUST verify that the initiating
user can read each Artifact. Course, assignment, and submission identifiers
MUST be resolved and authorized from their database relationships; arbitrary
client combinations are not authority.

If `artifacts:read` is granted, the token resource claim and command contain the
same Artifact IDs and version pins. Access is limited to:

```text
GET /api/v1/executions/{executionId}/artifacts/{artifactId}
GET /api/v1/executions/{executionId}/artifacts/{artifactId}/download
```

If `artifacts:write` is granted, an Extension may create a typed, versioned,
provenance-stamped output through:

```text
POST /api/v1/executions/{executionId}/artifacts
```

Artifact creation appends its lineage event in the same transaction. The
metadata API MUST expose only the version pinned to the Execution, not versions
created later. Protocol 1 output creation accepts `inlineJson` content and MUST
reject Extension-supplied `storageUri` values until FAIR provides a managed
upload capability.

## 8. Tools

Internal tools that run entirely inside an Extension remain private
implementation details. A platform-linked tool is used only when FAIR must
authorize or preserve the call.

Platform-linked invocation requires all of:

- parent token scope `tools:invoke`;
- target semantic capability ID in the parent's frozen `toolCapabilities`;
- target kind `tool` and enabled installation;
- valid input against the target's frozen schema;
- allowed declared effects in current course/assignment scope;
- a caller-provided idempotency key.

```text
POST /api/v1/executions/{parentExecutionId}/tools
GET  /api/v1/executions/{parentExecutionId}/tools/{toolExecutionId}
```

The first call creates a durable child tool Execution and a parent lineage
event. `(parentExecutionId, idempotencyKey)` is unique. The child uses the same
command, authorization, event, output validation, cancellation, and deadline
rules as every other capability. Reusing that key for different input or a
different target capability MUST return `409`.

## 9. Product replay and SSE

User-authenticated clients replay user-visible events through:

```text
GET /api/v1/executions/{executionId}/events?after_sequence={sequence}
GET /api/v1/executions/{executionId}/stream
Last-Event-ID: {sequence}
```

SSE is a view over the durable event log. It MUST NOT be used as the source of
truth or as a terminal signal. A terminal stream MUST drain every existing page
before closing. The current page limit is 500; backlogs larger than one page
are drained without polling delay. Private and operator events are excluded
from the user stream.

## 10. Simplicity constraints

- Do not add an agent-specific execution subsystem.
- Do not expose outbox, lease, or retry rows to assignment consumers.
- Do not create a second credential when the execution token can express the
  authority.
- Do not place authorization-relevant resource IDs only in arbitrary JSON.
- Do not require an agent framework or model provider.
- Do not interpret disconnects, timeouts, or process death as success.
- Prefer one explicit state transition and one durable identity over implicit
  heuristics.
- Add complexity only for a demonstrated safety or performance requirement.

## 11. Conformance evidence

The following tests are part of the protocol evidence:

| Claim | Test file |
| --- | --- |
| Strict contract and canonical fixture | `tests/test_execution_protocol_contract.py` |
| Body, target, time, and key signature verification | `tests/test_extension_command_signatures.py` |
| Token separation, scope, binding, expiry, revocation | `tests/test_execution_authorization.py` |
| Runner lease, ack, expiry, and redelivery | `tests/test_runner_protocol.py` |
| Framework-free raw HTTP happy path and duplicate retry | `tests/test_extension_protocol_conformance.py` |
| Webhook, projection rebuild, private visibility, SSE reconnect and multi-page drain | `tests/test_execution_e2e.py` |
| Cancellation, deadline, exactly-once terminal behavior | `tests/test_execution_lifecycle_protocol.py` |
| Interaction ownership and resume dispatch | `tests/test_execution_security.py` |
| Frozen Artifact inputs and execution-scoped access | `tests/test_artifact_api.py` |
| Authorized, idempotent child tool Execution | `tests/test_tool_invocation_protocol.py` |
| SQLite upgrade rehearsal | `tests/test_migration_rehearsal_files.py` |
| PostgreSQL JSONB, FK/cascade, and concurrent terminal race | `tests/test_postgres_compat.py` |

PostgreSQL conformance requires a disposable server URL in
`POSTGRES_TEST_URL`. Set `POSTGRES_TEST_STRICT=1` in CI to turn unavailable
PostgreSQL into a failure rather than a skip.

## 12. Non-goals for this phase

- Publishing standalone Python or TypeScript SDK packages.
- Selecting an agent framework, model provider, or prompt format.
- Building assignment chat UI.
- Moving private in-process tools into FAIR.
- Treating Flows as the primary assignment experience.

Those surfaces may build on Protocol 1 only after the raw boundary remains
conformant under retries, disconnects, restart, expiry, revocation,
cancellation, resume, and competing terminal outcomes.
