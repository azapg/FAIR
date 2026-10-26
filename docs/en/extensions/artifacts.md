---
title: Artifacts
description: Read versioned inputs and create outputs with provenance.
---

An **Artifact** is a typed input or output owned by FAIR. Examples include submission files, generated JSON, feedback, transcripts, and reports.

Artifacts are resources, not local file paths placed in a command.

## Read inputs

FAIR checks access before dispatch and pins the exact Artifact version. An Execution with `artifacts:read` can use:

```text
GET /api/v1/executions/{executionId}/artifacts/{artifactId}
GET /api/v1/executions/{executionId}/artifacts/{artifactId}/download
```

Later Artifact updates do not change the Execution's input.

## Create outputs

An Execution with `artifacts:write` can use:

```text
POST /api/v1/executions/{executionId}/artifacts
```

FAIR records the producing Execution and version lineage. Protocol 1 currently accepts managed `inlineJson` output.

<Warning>
TODO: Add managed binary upload. Extension-supplied storage paths remain rejected because they would bypass FAIR's authorization boundary.
</Warning>
