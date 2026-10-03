# 0007. Frontend feature folders

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

A layer-first `src/` spread one feature across many folders. Cross-feature dependencies were invisible.

## Decision

Organize `frontend/src/features/` by feature, then by flat layer folders. Each feature exposes `index.ts`. oxlint enforces the boundaries.

## Consequences

* Every cross-feature dependency is visible in an `index.ts`.
* Components cannot reach the network.
* Layer folders cannot have sub-folders.
