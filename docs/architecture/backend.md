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

`import-linter` enforces these rules:

* Services never import each other. A service that needs another service takes a port.
* Only `rag/services/agent_service/` and `rag/adapters/` import LangChain.
* Only `rag/container.py` constructs adapters, repositories and services.
* Routers never import `rag.domain` or `rag.config`.

## Services

`agent_service` is the only LangChain user. `rag_service` is the chat agent built on it.

`retrieval_service` finds the `RAG__TOP_K` closest passages, then passes them to a `RerankerPort`. With `RETRIEVAL__RERANK` on, that is `LlmReranker`: one structured LLM call scores each passage's summary from 1 to 10, and the passages are reordered by that score, with ties keeping the vector order. With it off, `NoReranker` keeps the vector order.

## Chat agent

Diagrams: [Agent graph](../diagrams/agent-graph.md), [Chat turn](../diagrams/chat-turn.md).

* `RagService` defines a `ToolAgentSpec`. `build_tool_agent` (`rag/services/agent_service/graphs/agent_builder.py`) turns the spec into a LangChain `create_agent` graph.
* `TopicalGuard` classifies each user message. Off-topic: it adds a decline instruction and keeps only `kind="user"` tools.
* `GroundednessGuard` checks each answer against this turn's `search_kb` results. Ungrounded: it sends the answer back, at most `RAG__MAX_REVISIONS` times.
* `CapabilityInstructions` adds each capability's instructions on every model call.
* A `Capability` gives the agent a feature: tools plus instructions. The owning service creates it. `agent_service` knows no feature by name.

## Streaming

A chat answer streams as Server-Sent Events: one JSON `data:` line per event, told apart by `type`.

1. `parse_event` (`rag/services/agent_service/streaming.py`) turns LangGraph events into domain events (`rag/domain/models/agent/stream.py`).
2. `to_stream_event` (`rag/api/schema/agent.py`) turns them into API models.
3. `applyEvent` (`frontend/src/features/chat/model/transcript.ts`) turns them into chat bubbles.

Event types: `text`, `reasoning`, `tool`, `todos`, `verification`, `retracted`, `references`. History replays the stored events through the same `applyEvent`.

## Errors

* Services raise an `AppError` subclass from `rag/domain/errors.py` with a `status_code`.
* One handler in `rag/app.py` turns every `AppError` into `{"detail": ...}`.
* `fastapi.HTTPException` is banned.

## Configuration

* Nested values use `__`: `LLM__API_KEY`, `RAG__TOP_K`.
* `LLM`, `OBSERVABILITY` and `KB_STORAGE` are discriminated unions on `BACKEND`.
