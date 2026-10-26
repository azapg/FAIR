---
title: Installations and grants
description: Connect an Extension and control where its Capabilities may run.
---

An **Installation** is one trusted copy of an Extension connected to FAIR. It stores the manifest snapshot, delivery settings, status, and credentials for that copy.

The same Extension can have multiple Installations. For example, a university may run one hosted installation while a researcher uses a local runner.

## Installation status

Only an enabled Installation can receive new work. Disabling it also invalidates its active execution authority.

## Grants

A **Grant** allows or denies a Capability in a context such as a platform, course, or assignment.

FAIR checks all of these before creating an Execution:

1. the user may perform the action;
2. the Installation is enabled;
3. the Capability and version exist;
4. a contextual Grant allows the requested effects.

The Extension does not decide whether it may access a submission, publish feedback, or propose a grade. FAIR makes that decision and sends only scoped authority.

## Credentials

A runner Installation receives a static credential for claiming commands. That credential cannot read educational data or report Execution results. The command contains a separate short-lived token for one Execution.

See [Security](/en/extensions/security) for the full credential model.

<Warning>
TODO: Add the end-user installation and grant workflow to the public Extension SDK guide.
</Warning>
