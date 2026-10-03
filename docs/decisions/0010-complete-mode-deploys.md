# 0010. Complete-mode Azure deploys

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

`Incremental` mode leaves removed or renamed resources behind. They keep billing.

## Decision

Deploy `infra/azure/main.bicep` with `--mode Complete` to a resource group used only by this app. Always run `what-if` first.

## Consequences

* Removed resources are deleted on the next deploy.
* Any resource in the group outside `main.bicep` is deleted too.
