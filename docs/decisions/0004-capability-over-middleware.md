# 0004. Agent features as capabilities

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

Preferences first lived inside `agent_service` as middleware. Each new feature would change `agent_service`.

## Decision

A feature gives the agent a `Capability`: tools plus instructions read on every model call. The feature's own service creates the capability. Middleware specs are only for how the agent runs: guards, planning.

## Consequences

* `agent_service` knows no feature by name.
* A feature is testable in its own service.
