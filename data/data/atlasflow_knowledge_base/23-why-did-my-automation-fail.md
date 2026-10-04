# Why Did My Automation Fail?

Automation failures usually come from configuration, permissions, or integration issues rather than a platform outage.

This guide lists the most common reasons an AtlasFlow automation may fail.

## 1. Missing permissions

An automation may attempt an action that the acting user, project, or connected credential is not allowed to perform.

Examples:

- creating a Jira issue in a project the integration can no longer access
- updating a workflow configuration without sufficient role privileges
- running an API-driven action with a token that no longer has the right scope

## 2. Missing or changed integration authorization

If an integration was reconnected, reauthorized, or partially reconfigured, the automation may lose access it previously had.

Common example:
- a Jira reconnect changed available scopes or invalidated an old project mapping

## 3. Rate limiting or downstream throttling

An automation that calls the AtlasFlow API or a third-party API too aggressively may begin failing or retrying unexpectedly.

Check for:

- 429 responses
- backoff handling
- large bursts of repeated triggers

## 4. Invalid conditions or stale references

An automation may reference:

- a field that no longer exists
- a project mapping that changed
- a status value that was renamed
- a condition that no longer matches current data

## 5. Workflow is paused

If the parent workflow or automation rule is paused, new automated runs do not start even if the trigger event occurs.

## 6. Draft vs published confusion

A very common cause of confusion is editing a draft and expecting live behavior to change immediately.

Remember:

- draft changes are not live until published
- already-running workflow instances may not pick up the new configuration

## Fast troubleshooting checklist

- confirm the workflow is published
- confirm it is not paused
- check integration authorization
- verify project and field mappings
- inspect rate-limit or retry behavior
- review recent configuration changes
