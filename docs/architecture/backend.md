# Backend

A layered FastAPI app in `rag/`. Domain ports separate business logic from infrastructure.

Diagram: [Backend layers](../diagrams/architecture.md#backend-layers).

## Layers

* **API** (`rag/api/`): routers, request and response schemas, `deps.py`. Reaches services only through `rag/api/deps.py`.
* **Services** (`rag/services/`): business logic, one package per service. Imports only `rag.domain`.
* **Domain** (`rag/domain/`): models, ports (`Protocol`s), `AppError` subclasses. Imports nothing else in `rag` and no LangChain.
* **Adapters** (`rag/adapters/`): wrapped third-party SDK clients.
* **Repository** (`rag/repository/`): SQL behind a domain port.
* **Config** (`rag/config/`): `Settings` and one module per settings section.
* **Shared** (`rag/shared/`): framework-free helpers any layer may use (e.g. `or_default`). Imports nothing else in `rag`.

`import-linter` enforces these rules:

* Services never import each other. A service that needs another service takes a port.
* Only `rag/services/agent_service/` and `rag/adapters/` import LangChain.
* Only `rag/container.py` constructs adapters, repositories and services.
* Routers never import `rag.domain` or `rag.config`.
* `rag.shared` imports nothing else in `rag`.

## Services

`agent_service` is the only LangChain user. `rag_service` is the chat agent built on it.

`retrieval_service` fetches the `RETRIEVAL__RETRIEVAL_CANDIDATES` best passages for the query. The search is hybrid, in one SQL query: a vector ranking of every chunk and a full-text ranking of the chunks matching any of the query's words (`content_tsv`, `ts_rank_cd`), fused by reciprocal rank (`1 / (60 + rank)` summed over both). With `RETRIEVAL__RERANK_CANDIDATES` above 0, it passes them to `LlmReranker`: one structured LLM call scores each passage's summary from 1 to 10, the passages are reordered by that score, with ties keeping the search order, and the first `RETRIEVAL__RERANK_CANDIDATES` are returned. At 0, `NoReranker` keeps the search order and every fetched passage is returned.

## Chat agent

Diagrams: [Agent graph](../diagrams/agent-graph.md), [Chat turn](../diagrams/chat-turn.md).

* `RagService` defines a `ToolAgentSpec`. `build_tool_agent` (`rag/services/agent_service/agent_builder.py`) turns the spec into a LangChain `create_agent` graph.
* `TopicalGuard` classifies each user message. Off-topic: it adds a decline instruction and keeps only `kind="user"` tools.
* `GroundednessGuard` checks each answer against this turn's `search_kb` results. Ungrounded: it sends the answer back, at most `LLM__MAX_REVISIONS` times. `AnswerGate` holds the answer back from the stream until the verdict, so a rejected answer never reaches the user.
* `CapabilityInstructions` adds each capability's instructions on every model call.
* A `Capability` gives the agent a feature: tools plus instructions. The owning service creates it. `agent_service` knows no feature by name.

## Streaming

A chat answer streams as Server-Sent Events: one JSON `data:` line per event, told apart by `type`.

1. `parse_event` (`rag/services/agent_service/streaming.py`) turns LangGraph events into domain events (`rag/domain/models/agent/stream.py`).
2. `to_stream_event` (`rag/api/schema/agent.py`) turns them into API models.
3. `applyEvent` (`frontend/src/features/chat/model/transcript.ts`) turns them into chat bubbles.

Event types: `text`, `reasoning`, `tool`, `todos`, `verification`, `references`, `error`. History replays the stored events through the same `applyEvent`.

A turn whose tool or model fails (after `ModelRetryMiddleware`'s retries) ends with an `error` event carrying a user-facing message, never the exception. `Agent.stream` also removes the failed turn from the agent's thread, so the same message can be sent again. The chat shows a Retry button on that error while it is the last bubble.

## Errors

* Services raise an `AppError` subclass from `rag/domain/errors.py` with a `status_code`.
* One handler in `rag/app.py` turns every `AppError` into `{"detail": ...}`.
* `fastapi.HTTPException` is banned.

## Configuration

* Nested values use `__`: `LLM__API_KEY`, `RETRIEVAL__RERANK_CANDIDATES`.
* `LLM`, `OBSERVABILITY` and `KB_STORAGE` are discriminated unions on `BACKEND`.
