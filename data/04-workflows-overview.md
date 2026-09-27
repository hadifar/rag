# Workflows Overview

Workflows are the core unit of repeatable work in AtlasFlow.

A workflow describes a business process that should happen consistently, such as onboarding a new employee, closing a month-end checklist, reviewing a vendor request, or approving access to an internal system.

## Workflow building blocks

A workflow can include:

- tasks
- approvals
- due dates
- conditions
- branching logic
- reminders
- integration steps
- status transitions

Workflows can be as simple as a short checklist or as complex as a multi-stage approval flow spanning several teams.

## Draft and published workflows

Each workflow exists in one of two major states:

### Draft
A draft workflow can be edited freely. Drafts are useful while building or reviewing a new process.

A draft workflow cannot be used for live operational runs until it is published.

### Published
A published workflow is the active version used for operational runs.

Changes made after publication are not applied to existing workflow runs unless explicitly stated by the change being made. In most cases, edits affect future runs rather than already-started ones.

## Manual and automated runs

A workflow can be started in two main ways.

### Manual run
A user starts the workflow directly, usually from the AtlasFlow interface or via API.

### Automated run
A trigger or condition starts the workflow automatically. Common examples include a scheduled start, a webhook event, or an integration event.

## Editing permissions

Workflow editing permissions depend on role and project permissions.

In general:

- Workspace Owners and Admins can create and edit workflows
- Members can create or edit workflows if project permissions allow it
- Viewers cannot edit workflows

## Common workflow controls

AtlasFlow supports several controls that are frequently relevant when troubleshooting workflow behavior:

### Pause
A paused workflow remains configured but does not start new runs until it is resumed.

### Archive
An archived workflow is removed from normal operational use and browsing, but historical data remains available according to retention rules.

### Version update
Publishing changes creates a new active configuration for future runs.

## Common causes of confusion

The following points often lead to misunderstandings:

- editing a draft does not change live behavior until the workflow is published
- pausing a workflow prevents new automated runs
- integration steps may fail even when the rest of the workflow is configured correctly
- permissions to view a workflow do not necessarily include permissions to edit it

## Best practice

For important operational workflows, AtlasFlow recommends:

- testing changes in draft before publication
- documenting any external integration dependencies
- reviewing permissions for users expected to edit or run the workflow
- checking pause status before diagnosing missing automated runs
