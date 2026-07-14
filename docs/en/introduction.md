---
title: Welcome to FAIR
description: An open LMS and research platform with optional, installed Extensions.
---

**FAIR** is an open-source learning platform and research environment built by the [Fair Grade Project](https://fairgradeproject.org). It gives professors, students, and researchers a controlled place to study how new technology affects education while keeping human judgment at the center.

FAIR is intentionally useful without AI. With no Extensions installed, it behaves like a focused LMS: people, courses, assignments, submissions, rubrics, artifacts, and human decisions remain available.

## Extensions add behavior

Installed Extensions add custom behavior such as:

- AI-assisted graders and feedback tools;
- course-aware teaching assistants;
- HTML slide and learning-material generators;
- transcription and document processing;
- deterministic analysis tools and external LMS connectors.

The platform does not embed those implementations or a global AI provider. It authenticates and authorizes an installed Extension, creates an observable Execution, records ordered events and Artifacts, and preserves the provenance needed for review and research.

Read [Core and Extensions](/en/platform/extension-architecture) for the foundational boundary.

## Reproducible research through Flows

A one-off task can be represented by one Execution. A **FlowVersion** pins an ordered procedure: exact capability versions, configuration, inputs, and linked step Executions. Researchers can then compare outcomes, costs, and interventions without depending on an opaque second workflow system.

Read [Flows and Executions](/en/platform/flows) for the current model and implementation status.

## Human judgment remains explicit

Extensions may analyze, explain, recommend, and propose. Completing an Execution does not silently publish a grade or make an institutional decision. Consequential outcomes remain explicit domain actions with visible human or policy provenance.

## Next steps

<Columns cols={2}>
  <Card title="Quickstart" icon="rocket" href="/en/quickstart">
    Run FAIR and create your first course.
  </Card>
  <Card title="Core and Extensions" icon="blocks" href="/en/platform/extension-architecture">
    Understand the boundary for every custom capability.
  </Card>
  <Card title="Flows and Executions" icon="workflow" href="/en/platform/flows">
    Learn how reproducible procedures share one execution substrate.
  </Card>
  <Card title="Roadmap" icon="map" href="/en/roadmap">
    Follow the path toward the FAIR 1.0 contract.
  </Card>
</Columns>
