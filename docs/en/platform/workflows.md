---
title: Workflows & Plugins
description: Explore the powerful workflows and plugins that make FAIR a versatile and customizable platform for your educational needs.
---

<Warning>Workflows and plugins are in active development and may change in future releases. Big missing features like TA Agents are not yet implemented. Check our [roadmap](/en/roadmap) for more information.</Warning>

Workflows and plugins are powerful tools that allow you to customize and extend the functionality of the FAIR platform. You can think of them as tiny scripts that process

## FAIR Core Extension (in development)
FAIR ships with a built-in **FAIR Core** extension that provides baseline transcriber, grader, reviewer, and rubric generation actions for workflows. This extension is still in development, and its behavior, settings, and available plugins may change as the platform evolves.

The core extension uses environment variables for default LLM configuration and exposes plugin settings to override model, base URL, temperature, and token limits at runtime. If you are testing workflows locally, start with the defaults and only override settings when you need to target a specific provider or model.

<Frame caption="Showcase of a workflow used to grade the submissions of the assignment Implementation and Analysis of Edge Detection Kernels">
    <img src="/assets/workflow.png" alt="Workflow diagram"   style={{height: "700px" }}/>
</Frame>
