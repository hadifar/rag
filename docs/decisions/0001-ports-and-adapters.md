# 0001. Ports and adapters in the backend

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

The backend uses LangChain, Postgres, Azure SDKs and an LLM provider. Business logic tied to these SDKs is hard to test and hard to change.

## Decision

Services depend only on `Protocol` ports in `rag/domain/ports/`. Adapters and repositories implement the ports. `rag/container.py` wires them. `import-linter` enforces the edges.

## Consequences

* Services run in unit tests with fakes.
* A new backend is a new class, not a branch in a consumer.
* A new dependency needs a port and a container line.
