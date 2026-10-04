---
title: Assignments and grading
description: Connect agents and graders to assignments without bypassing FAIR decisions.
---

Assignment agents and graders are Capabilities scoped to a course, assignment, or submission.

## Intended model

```text
Assignment action
  -> agent or grader Capability
  -> Execution
  -> streamed feedback and Artifacts
  -> proposal
  -> authorized FAIR decision
```

The Extension may analyze work and produce feedback or a grade proposal. FAIR owns the assignment record, authorization, rubric, review, and final published grade.

Submission files arrive as version-pinned Artifacts. Agent messages arrive as Events. Structured results are validated against the Capability output schema.

<Warning>
TODO: Finish the assignment-to-Capability binding, GradeProposal workflow, grading UI, and end-to-end external runner scenario. The underlying execution, streaming, Artifact, and authorization primitives are implemented.
</Warning>

Use a [Flow](/en/platform/flows) when a researcher needs a pinned, multi-step procedure. A normal assignment agent does not need a Flow.
