# Extension API & SDK: review and v2 proposal

Status: **partly implemented on `canary`.** Written against `e51145e`.

> **What shipped since this was written**
>
> - §2.1 cut platform-linked tools; §2.2 `supportsBatch`; §2.3 `kind` → `surface`;
>   §2.4 author-written JSON Schema (Surfaces and contracts supply them).
> - §4 Surfaces (`chat.agent`, `function`, `flow.step`) and the `function`
>   contract indirection, with `POST /api/v1/functions/invoke`.
> - §5 the TypeScript SDK, in `sdk/typescript/`, with the
>   pass-your-agent-in ergonomics from `api-plan/sdk-idea.md`.
> - Extension self-registration (`PUT /extensions/self/manifest`) plus
>   `fair ext bootstrap`, so §2.4's "install becomes paste a URL" is now
>   "install becomes run one command".
> - §3.4 wire casing: FAIR normalizes standard event payloads to camelCase at
>   the read boundary, and the frontend shim is gone.
>
> **Still open, and still recommended**
>
> - §3.1 the two identity tables (`extension_clients` /
>   `extension_installations`) are still separate.
> - §3.2 Installations remain deployment-wide. Neither deployment mode is
>   expressible yet. This is the biggest remaining gap.
> - §3.3 Flow definitions still embed `capabilityDefinitionId` UUIDs and still
>   chain only `previousOutput`.
> - §3.5 `declaredEffects` is still an open string list rather than a closed
>   enum.
>
> Three bugs turned up while wiring this end to end, all fixed, all of which the
> test suite had been masking — see the session notes at the end of §8.

Reviewed: `specs/extension-execution-protocol.md`, `src/fair_platform/extension_sdk/**`,
`src/fair_platform/backend/data/models/{extension,execution}.py`,
`src/fair_platform/backend/api/routers/{extensions,executions,artifacts,flows}.py`,
`src/fair_platform/backend/services/{extension_grants,flow_runtime,flow_service}.py`,
`docs/en/extensions/**`, `api-plan/sdk.md`, `frontend-dev/src/hooks/use-execution-chat.ts`.

---

## 0. The headline

**The execution protocol is good. Keep it. The problem is that it is also the developer-facing API.**

I went in expecting to recommend a simplification of Protocol 1 and came out
recommending the opposite: almost every rule in
`specs/extension-execution-protocol.md` is load-bearing. Idempotency keys,
exactly-one-terminal-outcome, execution-scoped tokens, version pinning, the
event log as source of truth, runner mode — these are the things that are
painful to add later and that make FAIR credible as a *research* platform.
Section 10 ("Simplicity constraints") is a genuinely good piece of engineering
discipline and it has mostly been followed.

The complexity you are feeling is real, but it is in a different place. Today a
developer who wants to ship a chat agent must understand: manifests, JSON Schema
Draft 2020-12, capability kinds, requested scopes, declared effects, tool
capabilities, four support flags, delivery modes, Ed25519 HTTP Message
Signatures, command idempotency, lease fencing, producer event identity,
message/part IDs, buffered delta flushing, and terminal-state rules — **to send
one string back to a user.**

That is a leak, not a design flaw. Protocol 1 says (§1) "Queue rows, leases,
retries, projection tables, and SSE fan-out are platform machinery. They MUST
NOT become required concepts in product or Extension APIs." That rule is
correct and is currently only half-enforced: the machinery is hidden, but the
*protocol* isn't.

So the recommendation is not a rewrite. It is:

1. **Cut four things** that are genuinely unearned complexity (§2).
2. **Fix three things** that are actively wrong or will block you (§3).
3. **Add one concept** — the Surface — that makes the whole thing extensible for
   the roadmap you described (§4).
4. **Put an SDK on top** that reduces the developer-facing concept count from
   ~17 to 4 (§5).

Concept count, developer-facing:

| | Today | Proposed |
|---|---|---|
| Must understand to ship a chat agent | ~17 | 4 (`Extension`, `Capability`, `ctx`, `Artifact`) |
| Must understand to ship a rubric generator | ~17 | 2 (`Extension`, `@ext.function`) |
| Protocol rules leaked into SDK surface | all | none |

Estimated work to get to "we can build content on this": **3–5 days**, because
most of it is deletion and an SDK, not new platform machinery.

---

## 1. What is genuinely good — do not touch

I want to be specific about this, because the temptation when simplifying is to
throw out the parts that look complex but are actually the parts you can't
rebuild later.

**Execution as the single unit of work.** One command shape for agents,
graders, flow steps, functions. `ExecutionCommand` is delivery-mode independent
(§3). This is exactly right and it is why adding new capability types later is
cheap.

**The event log as source of truth, SSE as a view.** §9: "SSE is a view over the
durable event log. It MUST NOT be used as the source of truth or as a terminal
signal." This is the single most valuable decision in the codebase. It gives you
reconnect, replay, audit, and research export for free, and it is the reason
your Flows can be reproducible at all.

**Exactly-one-terminal-outcome via row lock.** §6. "Stream closure, webhook
status, runner death, and process exit MUST NOT imply a terminal result." Most
platforms get this wrong and then spend a year on ghost executions.

**Execution token separation.** §4. The initiating user is in `sub`, the
installation is in `act.sub`, resources are typed claims, and FAIR never
forwards a user session. This already answers a question you raised about batch
installs (see §3.2) — you just haven't noticed that it does.

**Runner mode.** Long-poll `claim`/`ack` with lease fencing. This is rare and it
is a genuine competitive advantage for an academic platform: a professor can run
an extension on a lab machine behind NAT with no inbound firewall rule. Keep it.
It is also, notably, the delivery mode that makes local SDK development
pleasant — no ngrok.

**Version pinning / frozen manifest snapshot.** Non-negotiable for the Flows use
case you described.

**Buffered streaming, not one-event-per-token.** §5.2. Correct — see §6 on your
streaming question.

If I had to defend a single sentence of the current design it would be §5's
"The event log is authoritative." Everything good follows from it.

---

## 2. Cut list

Four features that cost real complexity and buy nothing for your v1 or your
stated roadmap.

### 2.1 Cut: platform-linked tools (child executions)

**You asked what these are and why you need them. My answer: you don't, and your
confusion is diagnostic.**

What they do: extension A's agent calls extension B's capability, and FAIR
authorizes, records, and validates the call as a child Execution.

What they cost:
- `tools:invoke` scope
- `toolCapabilities` manifest allowlist + its validator
  (`contracts/extension.py:tools_require_scope`)
- `kind: "tool"` as a load-bearing enum value
- child-execution lineage, `(parentExecutionId, idempotencyKey)` uniqueness
- 2 endpoints (`POST/GET /executions/{id}/tools`)
- `tool.invocation.created` event type
- an entire doc page (`docs/en/extensions/tools.md`) plus spec §8
- a test file (`tests/test_tool_invocation_protocol.py`)

What uses it: nothing in your v1 (agents, flows, rubric generators). Nothing in
your v2 (TA agents, notebooks, experiences). Cross-extension calls are a
marketplace feature, and you don't have a marketplace.

**But there is a real need hiding underneath it, and it's a different need.**

When you build the TA agent with RAG, the agent will want to *search course
materials*, *read a submission*, *create an artifact*, *award points*. Those are
not calls to another extension. They are calls to **FAIR**. That's the tool
surface you actually need, and it is much simpler: execution-scoped REST
endpoints plus SDK sugar. No allowlists, no child executions, no lineage
lattice.

```python
# What you need (FAIR as the tool provider)
@ext.agent(id="ta")
async def ta(turn, ctx):
    docs = await ctx.course.search(turn.text, limit=5)   # FAIR-provided
    async for chunk in llm.stream(prompt(docs, turn)):
        yield chunk
```

vs.

```python
# What tools currently gives you (extension as the tool provider)
result = await reporter.invoke_tool(
    capability_definition_id=UUID("cccccccc-..."),   # a UUID, by hand
    input={"query": turn.text},
    idempotency_key=f"{execution_id}:search:1",
)
```

Recommendation: **delete platform-linked tools from Protocol 1.** Replace with a
`fair.*` platform tool namespace exposed through `ctx` (§5.4). Re-introduce
extension→extension calls only when a second-party developer asks for it, at
which point it is additive and non-breaking.

Cost of cutting: ~400 lines of platform code, one doc page, one spec section,
one scope, one enum value, four manifest rules.

### 2.2 Cut: `supportsBatch`

Declared in `CapabilityManifest`, surfaced in the frontend capabilities table,
never read by any dispatch path. It has no defined semantics anywhere in the
spec. Delete it.

### 2.3 Cut: the `kind` enum (replace, see §4)

`kind: agent | grader | transformer | tool | integration`.

The docs say it plainly: *"The kind helps people discover the Capability. Every
kind uses the same Execution protocol."* So four of the five values are a
docstring rendered in a table. The fifth (`tool`) is load-bearing only for the
feature being cut in §2.1.

Meanwhile the thing FAIR *actually* needs to know — "where in the UI does this
appear and whose schema governs its I/O?" — is not expressible. `grader` and
`transformer` tell FAIR nothing actionable. This is replaced by Surfaces in §4.

### 2.4 Cut: author-written JSON Schema in manifests

Currently every capability must hand-write `inputSchema` and `outputSchema` as
Draft 2020-12 documents. Look at the canonical fixture — for an agent, the input
schema is `{"submissionId": {"type":"string","format":"uuid"}}`. That schema is
the same for every chat agent that will ever exist. Making each author write it
is busywork that also guarantees drift.

FAIR still needs frozen schemas — for output validation, for Flow pinning, for
replicability. So don't remove schemas from the *platform*. Remove them from the
*author*:

- **Surface-governed schemas** (chat, function contracts): FAIR owns them. The
  author writes nothing.
- **Author-defined schemas** (flow step outputs, custom function results): the
  SDK *derives* them from Python type hints / Zod and uploads them at register
  time.

Net: the platform's guarantees are unchanged; the author never types
`"$schema": "https://json-schema.org/draft/2020-12/schema"` again.

---

## 3. Fix list — things that are wrong or will block you

### 3.1 Two identity systems for the same thing

There are two tables keyed on `extension_id`, both with an enabled flag:

| | `extension_clients` | `extension_installations` |
|---|---|---|
| file | `models/extension_client.py` | `models/extension.py` |
| key | `extension_id` (PK) | `extension_id` (UNIQUE) |
| holds | secret hash, scopes, `enabled` | manifest, delivery, `status` |
| used by | runner claim/ack auth | dispatch, grants, capabilities |

These are one concept split across two tables with two lifecycles and two
enable/disable switches that can disagree. Disabling an installation does not
disable its client credential; the credential can still long-poll `claim`.

**Fix:** merge into one row. The registration owns the manifest, the delivery
config, the credential, and one status.

### 3.2 Installations do not model what you actually need

This is your biggest question and the schema currently answers "no" to all of
it.

Facts on the ground:
- `uq_extension_installations_extension_id` — **one installation per extension,
  globally.** But `docs/en/extensions/installations.md` says *"The same
  Extension can have multiple Installations. For example, a university may run
  one hosted installation while a researcher uses a local runner."* **The docs
  and the schema contradict each other.** The schema wins; the doc is wrong.
- `POST /extensions/installations` is admin-only (`_require_admin`) and takes a
  full hand-written manifest JSON body.
- There is no per-course, per-user, or per-org installation.
- The course "Capabilities" tab (`capabilities-tab.tsx`) is a read-only table of
  *every* capability on the deployment. It is not a course installation UI; it
  just looks like one.

So today: an extension is either on for the entire deployment or off. Neither of
your deployment modes is expressible.

**Fix: split the one conflated concept into three.** This is the single
clarifying move for installations.

| Concept | Question it answers | Scope | Who |
|---|---|---|---|
| **Registration** | Does this deployment know this extension exists? | deployment | admin, or built-in |
| **Installation** | Is it turned on *here*? | platform / org / course / user | varies by mode |
| **Grant** | What is it allowed to *do* here? | course / assignment | course owner |

Registration is what `extension_installations` + `extension_clients` become.
Installation is new. Grant already exists and is fine.

```python
class Installation(Base):
    __tablename__ = "extension_installations"
    id: UUID
    registration_id: UUID          # -> extension_registrations
    scope_type: str                # "platform" | "org" | "course" | "user"
    scope_id: UUID | None          # null for platform
    mode: str                      # "required" | "default_on" | "optional"
    enabled: bool
    installed_by_user_id: UUID
    config: dict                   # validated against configSchema

    __table_args__ = (
        UniqueConstraint("registration_id", "scope_type", "scope_id"),
    )
```

Resolution is a four-line rule:

```
active_in(course) =
    most specific Installation among
        (user, course, org, platform)
    where enabled,
    unless a more specific row disables it
    and the less specific row's mode != "required"
```

Now your two deployment modes fall out:

**Institutional batch install.** Admin registers the extension and creates one
Installation at `scope=platform, mode=required`. Every course has it, no
professor action, professors cannot turn it off. Change `mode` to `default_on`
and professors *can* opt out per course — one column, both policies. Batch
install into a subset of curricula = one Installation row per org/department
rather than per professor.

**Community/SaaS.** Extensions are registered as built-in at boot. Users get
`scope=user, mode=optional` rows. Enable/disable is a toggle on their own row.
Nobody is an admin. Exactly as simple as you wanted.

**"Will they use each course owner's permissions?"** — No, and the protocol
already gets this right. §4 puts the *initiating user* in `sub` and the
installation in `act.sub`. A platform-required extension invoked by a student
receives a token scoped to that student's resources. The installer's authority
is never borrowed. This is already correct; it just isn't documented, and it
should be stated loudly because it's the property that makes mandatory installs
safe. Add it to the security page.

**One more thing worth stating:** `mode=required` must not be able to escalate
grants. A required installation still needs explicit grants for consequential
effects (`feedback:write`, `grade:propose`). Institution mandates *availability*;
the course owner still authorizes *effects*. Keep those orthogonal or you will
have built a way for an admin to silently publish grades across a university.

### 3.3 Flows embed capability UUIDs — this breaks the research use case

`FlowNodeDefinition.capability_definition_id: UUID`.

A `CapabilityDefinition` UUID is a row ID in *one* FAIR database. So a Flow
definition today:

- cannot be written by hand,
- cannot be reviewed in a PR,
- cannot be published in a paper's appendix,
- cannot be re-run on another FAIR instance,
- cannot be shared with a collaborator.

For the feature whose entire purpose is *"our methodology is replicable"*, this
is the wrong primitive. The replicability you have is "the same database can
re-run it", which is not the claim a methods section makes.

**Fix:** definitions reference *portable coordinates*; pins are resolved at
publish time.

```jsonc
// Flow definition — portable, reviewable, publishable
{
  "mode": "ordered",
  "nodes": [
    { "id": "extract",
      "use": "org.fair.pdf@1.2.0#extract.text",
      "in":  { "file": "$.input.submission" } },
    { "id": "grade",
      "use": "org.example.grader@2.0.1#grade.essay",
      "in":  { "text":   "$.steps.extract.out.text",
               "rubric": "$.input.rubric" } }
  ]
}
```

At `POST /flows/{id}/versions/{v}/publish`, FAIR resolves each `use` to a
`CapabilityDefinition`, stores the pins in `capability_pins` (which already
exists and already does exactly this), and hashes the pair. The definition stays
text. **You already have the pin machinery — it's `flow_service._version_hash`
and `_pin`. This change is mostly deleting the UUID from the input type.**

**Second fix, same area:** `flow_runtime._step_input` passes only
`previousOutput`. Step 3 cannot see step 1's output. That breaks on the first
realistic pipeline — `extract → grade → format`, where `format` needs both the
grade and the original text. The `in:` mapping above fixes it with one JSON-path
resolver, and it also makes the data dependencies *explicit*, which is what you
want when comparing two Flows.

Keep `mode: "ordered"`. Do not add branching, parallelism, or a DAG. Linear plus
explicit input references covers benchmark pipelines and stays readable. If you
later need fan-out, `mode: "matrix"` is additive.

### 3.4 Wire casing is inconsistent (small but bleeding)

Spec §2: *"Wire JSON MUST use camel-case field aliases."* Envelopes comply.
Payloads do not — `ExecutionReporter.message_delta` emits `message_id`,
`part_id`; `execution_projection.py:144` reads `message_id`.

The frontend has already grown a compensating shim:

```ts
// use-execution-chat.ts:31
function payloadValue(payload: JsonRecord, field: string): unknown {
  if (field in payload) return payload[field];
  const camel = /* snake -> camel */;
  return payload[camel];
}
```

Every client in every language will now need that function. Pick camelCase
everywhere (the spec already did), fix the reporter and the projector, delete
the shim. Do it before the SDKs ship, because after that it's a breaking change
across languages.

### 3.5 Two permission vocabularies

`requestedScopes` (gates API routes) and `declaredEffects` (gates contextual
grants). Both are free-form string lists on the manifest. Authors must learn
which is which and there is no enumeration of valid values anywhere.

For v1, most extensions want: read the inputs, write output, stream. That should
be implied by the surface, not declared. Recommendation:

- **Scopes become implicit.** A `chat.agent` capability gets
  `executions:events` + `artifacts:read` + `artifacts:write` automatically. A
  `function` gets `executions:events`. Nobody declares them.
- **Effects stay explicit but become a closed enum** — `feedback:write`,
  `grade:propose`, `points:award`, `notify:user`, `external:network`. These are
  the consequential things a human approves. A closed set means you can render
  a real consent UI instead of a string list.

One vocabulary the author writes, one the platform infers.

---

## 4. The one concept to add: **Surfaces**

This is the part that makes the roadmap work, so I want to make the case
carefully.

### The problem

You described three v1 needs and three v2 needs. Try expressing them with
`kind`:

| Need | `kind` | Does `kind` tell FAIR what to do? |
|---|---|---|
| Chat agent in model selector | `agent` | no — where does it appear? |
| Flow step | any | no |
| Rubric generator button | `transformer`? | no — which button? what input? |
| Course TA agent | `agent` | no — how is it different from chat? |
| Notebook cell | `transformer`? | no |
| Leaderboard experience | `integration`? | no |

`kind` is a label. What FAIR needs is a **contract + placement**: what shape is
the I/O, and where in the product does this show up?

### The proposal

A **Surface** is a FAIR-owned contract. FAIR defines the input schema, the
output schema, the UI placement, and the lifecycle semantics. An extension picks
a surface and implements it.

```
Capability = Surface + implementation
```

v1 surfaces — exactly your three needs:

| Surface | Placement | Input (FAIR-owned) | Output | Lifecycle |
|---|---|---|---|---|
| `chat.agent` | model selector, chat threads | thread messages, attachments, course/assignment scope | message events + artifacts | streaming, cancellable, resumable |
| `function` | contextual buttons, keyed by `contract` | contract-defined | contract-defined | request/response |
| `flow.step` | Flow node picker | node `in:` mapping | author-declared JSON | request/response |

v2 surfaces — **added without touching the protocol**:

| Surface | Placement | Notes |
|---|---|---|
| `course.agent` | course sidebar, always-on TA | `chat.agent` + course-corpus scope + RAG hooks |
| `notebook.cell` | notebook | input: prompt + course materials; output: artifact |
| `experience` | course nav, custom route | bundles agents + artifacts + storage + a UI slot |

The critical property: **adding a surface is adding a contract to a registry,
not changing the execution protocol.** Every surface still compiles to one
`ExecutionCommand` and one event log. That's what §1 of the spec was protecting
and this preserves it.

### Functions and contracts — your "rubric generator" generalized

You said: *"Functions like that we might have a lot."* Right. So make the
function surface generic and the *contract* the extensible part.

```
surface: function
contract: fair.rubric.generate@1
```

FAIR maintains a contract registry — literally a directory of typed I/O
definitions:

```
contracts/
  fair.rubric.generate@1        # (assignment context, constraints) -> Rubric
  fair.course.describe@1        # (course title, syllabus?) -> description
  fair.term.define@1            # (term, course context) -> definition
  fair.assignment.draft@1       # (topic, level) -> assignment draft
```

Adding "autocomplete course descriptions" later is: write one contract file,
render one button. Zero protocol work, zero SDK version bump. Extensions that
implement it light up automatically. **This is the mechanism that lets you "add
a bunch of new features" the way you described.**

The UI story falls out too. `docs` says rubric generators should appear in the
Rubrics tab *and* in "you have no rubrics" empty states. So placement is a
property of the *contract*, not the extension:

```jsonc
// contracts/fair.rubric.generate@1.json  (FAIR-owned)
{
  "id": "fair.rubric.generate@1",
  "title": "Generate a rubric",
  "input":  { /* JSON Schema, FAIR-owned */ },
  "output": { /* JSON Schema, FAIR-owned */ },
  "placements": [
    { "route": "/rubrics",            "slot": "toolbar" },
    { "route": "/assignments/new",    "slot": "rubric-empty-state" }
  ]
}
```

The frontend renders a button wherever a contract declares a placement and at
least one installed extension implements it. One generic component, N features.

### Does this hold up for "Experiences"?

Let me stress-test with your Leaderboard, since you said it should set the tone.

```python
ext = Extension(id="org.math.leaderboard", name="Leaderboard", version="1.0.0")

@ext.experience(id="leaderboard", route="/leaderboard", nav="Leaderboard")
async def board(ctx):
    scores = await ctx.storage.query("scores", order_by="-points", limit=50)
    return ctx.artifact.html(render(scores))       # rendered in web/mobile client

@ext.agent(id="coach", surface="course.agent")
async def coach(turn, ctx):
    async for chunk in llm.stream(turn.messages):
        yield chunk
    if await judged_understanding(turn):
        await ctx.effects.award_points(turn.user, 10)   # gated by points:award grant

@ext.function("org.math.problem.generate@1")
async def problem(input, ctx):
    return {"html": interactive_problem(input.topic, input.difficulty)}
```

Everything it needs already exists or is one additive step:
- multiple capabilities per extension — exists
- artifacts as interactive HTML — exists (`specs/artifacts.md`), needs the
  managed binary upload that's already on the TODO list
- points as a granted effect — new closed-enum value, one row
- extension-scoped storage — new, small, and clearly needed
- a UI slot — new frontend, no protocol change

No protocol change. The architecture holds. I'm reasonably confident this is the
right shape.

---

## 5. The SDK

Working backwards from what you want to write, as you asked.

### 5.1 Design rules

1. **Protocol is invisible.** No developer types `producerEventId`,
   `idempotencyKey`, `message.delta`, or `visibility`.
2. **Framework-agnostic by adapter, not by abstraction.** Don't invent a FAIR
   agent type. Accept AI SDK / LangChain / raw generators, and translate.
3. **Schemas are derived, never written.** Zod / Pydantic in, JSON Schema out.
4. **Local dev is one command with no tunnel** — runner mode makes this free.
5. **Failures are loud.** No silent degradation when an adapter doesn't match.

### 5.2 TypeScript (ship first — the AI SDK is stable there)

```ts
import { createExtension, agent, fn, flowStep } from "@fair/sdk";
import { streamText } from "ai";
import { openai } from "@ai-sdk/openai";
import { z } from "zod";

export default createExtension({
  id: "org.example.tutor",
  name: "Socratic Tutor",
  version: "1.0.0",

  capabilities: [
    // -> appears in the model selector
    agent({
      id: "tutor",
      name: "Socratic Tutor",
      description: "Guides students without giving answers.",
      async run({ messages, attachments, course }, ctx) {
        const docs = await ctx.course.search(messages.at(-1)!.text);
        return streamText({
          model: openai("gpt-5"),
          system: `Never give the answer. Context:\n${docs}`,
          messages,
        });
      },
    }),

    // -> appears as a button wherever the contract declares a placement
    fn({
      contract: "fair.rubric.generate@1",   // input/output types come from here
      async run(input, ctx) {
        const { object } = await generateObject({
          model: openai("gpt-5"),
          schema: ctx.contract.outputSchema,
          prompt: `Rubric for: ${input.assignment.title}`,
        });
        return object;
      },
    }),

    // -> selectable as a Flow node
    flowStep({
      id: "grade.essay",
      input:  z.object({ text: z.string(), rubric: z.any() }),
      output: z.object({ score: z.number(), feedback: z.string() }),
      async run({ text, rubric }, ctx) {
        return await grade(text, rubric);
      },
    }),
  ],
});
```

`return streamText(...)` is the whole streaming story. The SDK consumes the AI
SDK stream, buffers to 100ms/2KB, emits `message.started` / `message.delta` /
`message.completed` with stable producer IDs, handles token refresh, and emits
exactly one terminal event — including on throw, on cancel, and on process
death (via the runner lease).

### 5.3 Python

Two forms. The decorator form is the supported path; the object form is the
sugar you sketched.

```python
from fair import Extension
from fair.contracts import RubricGenerate

ext = Extension(id="org.example.tutor", name="Socratic Tutor", version="1.0.0")

@ext.agent(id="tutor", name="Socratic Tutor")
async def tutor(turn, ctx):
    docs = await ctx.course.search(turn.text, limit=5)
    async for chunk in llm.stream(prompt(docs, turn.messages)):
        yield chunk                      # buffering is the SDK's problem

@ext.function(RubricGenerate)            # typed from the contract registry
async def rubric(input: RubricGenerate.Input, ctx) -> RubricGenerate.Output:
    return RubricGenerate.Output(criteria=[...])

@ext.flow_step(id="grade.essay")
async def grade(text: str, rubric: dict, ctx) -> GradeResult:   # schema derived
    ...

if __name__ == "__main__":
    ext.run()          # runner mode, long-polls, no tunnel, no inbound port
```

`yield` is the correct Python streaming primitive. Everything the developer
needs to know about `message.delta` is: *don't*.

And your sketch, supported:

```python
import ai
from fair import Extension, AgentCapability

agent = ai.Agent(model="gpt-5", tools=[contact_mothership])

ext = Extension(
    id="org.example.tutor",
    name="Socratic Tutor",
    version="1.0.0",
    capabilities=[AgentCapability(id="tutor", agent=agent)],
)
```

**One honest caveat.** You described this as "we would try to inject a
middleware into it to get all the tool calls, errors and so on reported back to
FAIR without you having to modify anything." That works, and it's the right
goal — but auto-detecting and monkey-patching arbitrary agent objects is exactly
where SDKs become flaky and where debugging becomes miserable for the developer.

Recommendation: **explicit adapters, registered by type.**

```python
# fair/adapters/vercel_ai.py
@register_adapter(ai.Agent)
class VercelAIAdapter(AgentAdapter):
    def instrument(self, agent, reporter): ...
```

`AgentCapability(agent=x)` looks up the adapter for `type(x)`. If none is
registered it raises at *import* time with a clear message
(`No FAIR adapter for langchain.AgentExecutor. Install fair-langchain, or use
@ext.agent for full control.`) rather than degrading silently at runtime. Same
ergonomics, failures land at the developer's feet instead of in your logs.

Ship adapters for AI SDK (TS), then AI SDK (Python) when it stabilizes, then
raw-generator (always works). That's enough.

### 5.4 What `ctx` exposes

This replaces the tools feature (§2.1) and is the surface that will grow.

```python
ctx.course.search(query, limit)        # RAG over course materials
ctx.course.materials()                 # list
ctx.artifacts.read(id)                 # version-pinned inputs
ctx.artifacts.create(...)              # provenance-stamped output
ctx.artifacts.html(markup)             # interactive artifact
ctx.storage                            # extension-scoped KV/table, per course
ctx.ask(question, schema=...)          # interaction request -> resume, awaited
ctx.effects.award_points(user, n)      # grant-gated
ctx.log / ctx.progress
ctx.user, ctx.course, ctx.assignment   # already-authorized scope
```

`ctx.ask()` deserves note: `interaction.requested` → `waiting` → user resolves →
`resume` command is genuinely hard to write by hand and trivially expressible as
an awaited call. The SDK re-enters the handler on resume and replays to the
await point. That is the kind of thing that justifies an SDK existing.

---

## 6. Your streaming question

> *I'm not sure whether token streaming is real time or if that will be a pain
> for developers... they have to do a bunch of requests and it will look laggy.*

Short answer: **it will not look laggy, and developers will never see it.** But
there is a real cost, and it isn't the one you're worried about.

**Latency.** The current default flushes at 100ms or 2048 chars. At typical LLM
throughput that's ~5–10 tokens per chunk. Human reading speed is ~250 wpm ≈ 4
words/second. A 100ms chunk is well below the threshold where text streaming
stops looking continuous — this is roughly what most chat UIs do anyway, since
rendering per-token is wasteful. Added latency vs. direct provider streaming is
one extension→FAIR round trip, ~10–50ms same-region. Imperceptible.

**The actual cost is request volume, not latency.** A 60-second response is
~600 POSTs. 100 concurrent chats is ~1,000 req/s of event ingest, each taking a
row lock on the Execution (§5). That's your scaling wall, and it arrives at a
few hundred concurrent streams — not soon, but not never.

**Recommendations:**

1. **Ship as-is for v1.** It is correct, it is durable, and the numbers are fine
   at your scale. Do not optimize this yet.
2. **Make the ingest endpoint content-type polymorphic now** so the fix is
   additive later: accept `application/json` (batch, today) and reserve
   `application/x-ndjson` (one long-lived streaming POST, many event frames, one
   connection, same durable log, same idempotency). This is a one-line
   forward-compatibility decision and it costs nothing today.
3. **Tune per surface, not globally.** Chat wants 100ms. A flow step wants
   whatever's cheapest. Let the surface set the default; developers never touch
   it.
4. **Never expose the knob in the SDK's happy path.** `yield chunk` /
   `return streamText(...)`. If a developer is thinking about flush intervals,
   the SDK has failed.

One thing to *not* do: don't let extensions stream directly to the browser to
avoid the hop. It would cost you replay, reconnect, audit, research export, and
the single-source-of-truth property — the most valuable thing you have — to save
30ms nobody can perceive.

---

## 7. Concrete diff summary

### Delete
- `POST/GET /executions/{id}/tools`, `tools:invoke`, `toolCapabilities`,
  `tool.invocation.created`, spec §8, `docs/en/extensions/tools.md`
- `supportsBatch`
- `kind` enum (→ `surface`)
- `extension_clients` table (merge into registration)
- author-written `inputSchema`/`outputSchema` for surface-governed capabilities

### Change
- `CapabilityDefinition.kind` → `surface` + `contract`
- `Installation` split into `ExtensionRegistration` + scoped `Installation`
  (`scope_type`, `scope_id`, `mode`)
- `FlowNodeDefinition.capability_definition_id: UUID` → `use: str` +
  `in: dict[str, JsonPath]`
- event payload keys → camelCase; delete `payloadValue()` shim
- `requestedScopes` inferred from surface; `declaredEffects` → closed enum

### Add
- Surface registry (3 surfaces v1)
- Contract registry (`fair.rubric.generate@1` + placements)
- `ctx.*` platform API (course search, storage, effects, ask)
- `@fair/sdk` (TS), `fair` (Python)
- `GET /.well-known/fair-extension` self-describing manifest — install becomes
  "paste a URL", not "paste a manifest"

### Keep, unchanged
Everything in §1.

---

## 8. Sequencing — what to do in the next few days

Ordered so that each step leaves the tree working and the earliest step unblocks
content creation.

**Day 1 — deletion and casing.** Cut tools, `supportsBatch`, `kind`. Fix payload
casing end to end and delete the frontend shim. This is pure subtraction and it
shrinks everything that follows. No new concepts.

**Day 2 — surfaces + contracts.** Add `surface` and `contract` to
`CapabilityDefinition`. Define `chat.agent`, `function`, `flow.step`. Write
`fair.rubric.generate@1` with its two placements. Render the generic
contract-button component.

**Day 3–4 — the SDK (TypeScript).** `createExtension`, `agent`, `fn`,
`flowStep`, runner transport, AI SDK adapter, `ctx` with artifacts + ask. Target:
the tutor example in §5.2 runs end to end against a local FAIR.

**Day 4 — installations.** Registration/Installation split, scope + mode,
resolution rule, `/.well-known/fair-extension`. Deferrable if you only need
platform-scope installs this week — but do it before any institutional pilot.

**Day 5 — flows portability.** `use:` coordinates + `in:` mapping. Deferrable
until you actually run a benchmark, but do it before anyone authors a Flow you'd
have to migrate.

### Bugs found by building the vertical slice

Three real defects surfaced only once a real Extension ran against a real
server. All three were green in CI, which is the interesting part.

1. **Execution artifact creation was broken in production.** The app session
   runs `autoflush=False`; the test fixture used SQLAlchemy's default `True`.
   `finalize_artifact_version()` looks the version up with a `SELECT`, so in
   production it never saw the just-added rows and every call failed with
   "ArtifactVersion does not exist". Fixed with an explicit flush, and
   `tests/conftest.py` now matches the app's session settings so this class of
   divergence cannot hide again.

2. **Artifact finalization tripped its own immutability guard.** In one flush
   SQLAlchemy writes the parent `ArtifactVersion` before its parts, so marking
   the version terminal first made the part-hash updates violate the "parts of
   terminal ArtifactVersion are immutable" trigger. Fixed by flushing part
   hashes while the version is still a draft. Invisible to tests because the
   trigger comes from a migration and tests build schema with `create_all()`.

3. **Two dispatch paths disagreed about the payload shape.** Chat enqueued the
   raw input; Flow enqueued `{execution_id, capability_id, capability_version,
   input}`. The canonical fixture says `payload.input`. Unified on the fixture:
   every path enqueues just the input, since identity and capability pin
   already travel in the command envelope.

The general lesson worth keeping: the test fixtures were more permissive than
production in two independent ways (autoflush, schema creation). Both hid real
bugs. Fixture/production parity is worth auditing beyond these two cases.

**Then: dogfood, and make it a rule.**

> FAIR's own default chat agent and default rubric generator ship as extensions
> built on the public SDK, with no privileged access.

I'd argue this is the most important line in the document. It is the only
mechanism that reliably keeps an SDK honest — every gap you'd otherwise paper
over with an internal shortcut becomes something you have to fix properly. It
also means "start adding content in the next few days" and "build the SDK" are
the same task rather than competing ones.

---

## 9. Open questions for you

1. **Contract registry ownership.** FAIR-owned only (curated, consistent) or can
   extensions define contracts other extensions implement (extensible, becomes a
   standards problem)? I'd start FAIR-owned.
2. **`mode=required` and grants.** I've assumed a mandated install still can't
   self-grant consequential effects (§3.2). Confirm — it's a policy call with
   real consequences.
3. **Extension storage.** Needed for Experiences. Scope it per
   `(extension, course)`? Quota? Is it exportable as research data?
4. **Python vs TypeScript first.** I've assumed TS first (AI SDK stable) with
   Python following. Your users are researchers, who are overwhelmingly Python.
   If Python-first matters more than AI-SDK-adapter quality, invert it — the
   raw-generator adapter works fine today and doesn't depend on
   `vercel-labs/ai-python` stabilizing.
5. **Does `grader` need to be a surface?** I folded grading into `function` +
   contract (`fair.grade.propose@1`). If grading needs streaming feedback and a
   review workflow, it may deserve its own surface. I lean toward contract, but
   I haven't read the GradeProposal design closely.
