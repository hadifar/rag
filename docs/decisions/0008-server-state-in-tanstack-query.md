# 0008. Server state in TanStack Query

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

Server data was loaded in effects and held in contexts. Caching, retries and invalidation were hand-written per feature.

## Decision

Hold server data in the TanStack Query cache. Read and change it only in feature hooks. Keep `AuthProvider` as the only app-wide context.

## Consequences

* One retry policy (`shouldRetry`).
* The live chat answer and its history share one cache entry.
* Components never import `@tanstack/react-query`.
