---
title: SDK Examples
description: Practical examples for building Fair Platform plugins and integrating them into workflows.
---

This page contains **starter examples** for the Fair Platform SDK.

> Status: This is an initial placeholder page to prevent 404s while the examples are being expanded.

## What you’ll find here

These examples will focus on:

- Creating a minimal plugin with settings
- Reading artifacts and producing derived artifacts
- Returning grades/feedback objects in a consistent way
- Registering plugins so the backend can discover them
- Local development workflow for iterating on plugins

## Example 1: Minimal “Hello Plugin” (structure)

A typical plugin will include:

- A class implementing the appropriate base type (grader / transcriber / validator / storage)
- A settings model (so UI + API can validate config)
- A `run(...)`-style method that receives platform context and produces outputs

```/dev/null/sdk-examples-hello-plugin.txt#L1-23
# Pseudocode (placeholder)
class ExamplePlugin(BasePlugin):
    name = "example"

    class Settings(BaseModel):
        enabled: bool = True

    def run(self, submission, assignment, settings: Settings):
        if not settings.enabled:
            return None
        return {"message": "hello"}
```

## Example 2: Artifact in → artifact out

Many workflows look like:

1. Input artifact (e.g., PDF/image/zip)
2. Plugin extracts/normalizes
3. Output artifact (e.g., extracted text, parsed notebook, execution logs)

```/dev/null/sdk-examples-artifacts.txt#L1-26
# Pseudocode (placeholder)
def run(self, submission, assignment, settings):
    source = select_artifact(submission.artifacts, kind="file")
    text = extract_text(source.bytes)
    derived = Artifact(kind="text", content=text)
    return {"artifacts": [derived]}
```

## Example 3: Grader output shape (high level)

Graders usually produce:

- Score/grade
- Rubric categories (optional)
- Feedback/comments
- Flags/warnings (optional)

```/dev/null/sdk-examples-grader.txt#L1-28
# Pseudocode (placeholder)
def grade(self, submission, assignment, settings):
    return {
        "score": 0.92,
        "feedback": "Good work. Improve clarity in section 2.",
        "flags": ["needs-citations"]
    }
```

## Next steps

- `en/sdk/overview`
- `en/sdk/plugins`
- `en/sdk/schemas`

If you tell me which plugin type you want first (OCR transcriber, rubric grader, code runner, validator, storage), I can turn one of the pseudocode blocks above into a concrete example aligned with the current SDK implementation.