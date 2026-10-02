# 0002. One Postgres database for all state

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

The app stores users, conversations, agent checkpoints, preferences and vector embeddings. Each could live in a separate store.

## Decision

Store all state in one Postgres database with `pgvector`. Alembic owns `public`. The LangGraph checkpointer owns the `langgraph` schema. No in-memory mode.

## Consequences

* One service to run, back up and secure.
* Constraints and transactions span all app tables.
* Hybrid search runs in SQL.
* Two schema owners in one database.
