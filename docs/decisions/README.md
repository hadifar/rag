# Architecture decisions

One file per decision. Never edit an accepted decision. Write a new decision that supersedes the old one.

| # | Decision | Status |
|---|---|---|
| [0001](0001-ports-and-adapters.md) | Ports and adapters in the backend | Accepted |
| [0002](0002-postgres-for-all-state.md) | One Postgres database for all state | Accepted |
| [0003](0003-self-hosted-auth.md) | Self-hosted JWT auth | Accepted |
| [0004](0004-capability-over-middleware.md) | Agent features as capabilities | Accepted |
| [0005](0005-transcript-separate-from-checkpoint.md) | Transcript separate from the agent checkpoint | Accepted |
| [0006](0006-append-only-migrations.md) | Append-only migrations | Accepted |
| [0007](0007-frontend-feature-folders.md) | Frontend feature folders | Accepted |
| [0008](0008-server-state-in-tanstack-query.md) | Server state in TanStack Query | Accepted |
| [0009](0009-same-origin-proxy.md) | Same-origin `/api` proxy | Accepted |
| [0010](0010-complete-mode-deploys.md) | Complete-mode Azure deploys | Accepted |

## Add a decision

1. Copy the template below to `docs/decisions/NNNN-<kebab-title>.md` with the next number.
2. Add the row to the table above.
3. If the decision replaces another, set the old status to `Superseded by NNNN`.

```md
# NNNN. <Title>

Status: Proposed | Accepted | Superseded by NNNN
Date: YYYY-MM-DD

## Context
<The problem and the forces.>

## Decision
<The choice, in one or two sentences.>

## Consequences
* <What gets easier.>
* <What gets harder.>
```
