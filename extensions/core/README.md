# FAIR Core Extension

FAIR's own built-in capabilities, written on the public `@fair/sdk` with no
privileged access. This is the dogfooding rule: if something here needs a
shortcut the SDK does not offer, that is a bug in the SDK, not a reason for a
private API.

It is also the reference for what the SDK can do.

## What is in here

| File | Surface | What it shows |
| --- | --- | --- |
| `src/tutor.ts` | `chat.agent` | hand an **unmodified AI SDK agent** to FAIR (local `gemma3:270m` via Ollama) |
| `src/echo.ts` | `chat.agent` | the `run` form — yield strings, no model needed |
| `src/rubric.ts` | `function` | implement the `fair.rubric.generate@1` contract |
| `src/flow-steps.ts` | `flow.step` | three pinnable nodes for a reproducible Flow |

## Running it

From the repo root, with FAIR running on `:8000`:

```bash
bun install
bun run build:sdk

fair ext bootstrap fair.core          # prints the secret once

cd extensions/core
FAIR_PLATFORM_URL=http://127.0.0.1:8000 \
FAIR_EXTENSION_SECRET=<secret> \
bun run dev
```

```text
[fair] fair.core v0.1.0 ready (6 capabilities, runner alam:33396)
[fair]   - chat.agent: tutor
[fair]   - chat.agent: echo
[fair]   - function: fair.rubric.generate
[fair]   - flow.step: extract.text
[fair]   - flow.step: score.text
[fair]   - flow.step: summarize.result
```

`tutor` and `echo` now appear in FAIR's model selector at `/chat/live`.

### The Ollama tutor

`tutor` expects Ollama on `http://127.0.0.1:11434` with `gemma3:270m`:

```bash
ollama pull gemma3:270m
```

Override with `OLLAMA_URL` and `OLLAMA_MODEL`. `gemma3:270m` is a 270M-parameter
model — its answers are not good, which is the point: it makes token streaming
easy to watch without a provider key.

Use `echo` if you have no model at all; it exercises the same streaming path.

## Verifying

From the repo root:

```bash
uv run python scripts/e2e_chat_demo.py --capability echo
uv run python scripts/e2e_chat_demo.py --capability tutor
uv run python scripts/e2e_flow_demo.py
```

The flow demo builds `extract -> score -> summarize`, publishes it (which pins
every node's capability version), runs it, and leaves a finalized artifact
behind. The steps are deliberately trivial and model-free: the demo is about
pinning and reproducibility, not about grading quality.
