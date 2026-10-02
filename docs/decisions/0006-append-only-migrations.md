# 0006. Append-only migrations

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

A database that already ran a migration ignores later edits to that migration. The schema then drifts silently.

## Decision

Never change a committed migration. The `migrations-append-only` hook and the CI `commitizen` job enforce the rule. Use `SKIP=migrations-append-only` only for a deliberate exception.

## Consequences

* Every schema change is a new revision.
* Every migration needs a working `downgrade()`.
