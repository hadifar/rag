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

`agent_service` is the only LangChain user: single-shot generation (`LLMServicePort`) and the chat agent (`ChatAgentPort`).

`retrieval_service` fetches the `RETRIEVAL__RETRIEVAL_CANDIDATES` best passages for the query. The search is hybrid, in one SQL query: a vector ranking of every chunk and a full-text ranking of the chunks matching any of the query's words (`content_tsv`, `ts_rank_cd`), fused by reciprocal rank (`1 / (60 + rank)` summed over both). With `RETRIEVAL__RERANK_CANDIDATES` above 0, it passes them to `LlmReranker`: one structured LLM call scores each passage's summary from 1 to 10, the passages are reordered by that score, with ties keeping the search order, and the first `RETRIEVAL__RERANK_CANDIDATES` are returned. At 0, `NoReranker` keeps the search order and every fetched passage is returned.

## Chat agent

Diagrams: [Agent graph](../diagrams/agent-graph.md), [Chat turn](../diagrams/chat-turn.md).

* Free text a user types (a chat message, a preference) is a `UserText` field (`rag/api/schema/text.py`): `normalize_text` (`rag/shared/text_normalizer.py`) applies NFKC, drops control, invisible and bidi-override characters, and tidies whitespace before the length checks run.
* `ChatAgent` (`rag/services/agent_service/agent.py`) is the agent: a LangGraph `StateGraph` with four nodes, `classify` → `model` ⇄ `tools`, then `verify`, and `stream()`, which runs it one turn at a time (`AgentTurn`). Its tools are in `tools.py`, its prompts in `prompts.py`, and the guards' checks are plain functions in `guards/`. `AgentService` is only single-shot generation, for titles and reranking.
* `classify` (`guards/off_topic.py`) classifies each user message, with the two turns before it, as `allow`, `restrict` or `block`, against `OFF_TOPIC_SCOPE`. Restrict (off-topic): the `model` node adds `OFF_TOPIC_INSTRUCTION` and binds only the `USER_TOOLS` (the preference tools). Block (injection, jailbreak, harmful): the turn ends before the model runs, the user gets `BLOCKED_MESSAGE`, and the agent does not remember the message. All three are in `rag/services/agent_service/prompts.py`.
* Both guards get a structured verdict (a Pydantic schema) from their LLM call. A failed call passes the message or answer (fail open).
* `verify` (`guards/groundedness.py`) checks each answer against this turn's `search_kb` results. Ungrounded: it sends the answer back, at most `MAX_REVISIONS` times. `AnswerGate` holds the answer back from the stream until the verdict, so a rejected answer never reaches the user.
* The `model` node adds the user's saved preferences on every model call, read fresh each time. The preference tools (`save_user_preference`, `forget_user_preference`) and the instructions reach `PreferenceService` through `PreferencesPort`.

## Streaming

A chat answer streams as Server-Sent Events: one JSON `data:` line per event, told apart by `type`.

1. `parse_event` (`rag/services/agent_service/streaming.py`) turns LangGraph events into domain events (`rag/domain/models/agent/stream.py`).
2. `to_stream_event` (`rag/api/schema/chat.py`) turns them into API models.
3. `applyEvent` (`frontend/src/features/chat/model/transcript.ts`) turns them into chat bubbles.

Event types: `text`, `reasoning`, `tool`, `todos`, `verification`, `artifacts`, `error`. History replays the stored events through the same `applyEvent`.

`artifacts` is sent once the turn is done, if a tool returned an artifact (`response_format="content_and_artifact"`): what the tools handed the user (today, the knowledge-base sources a search found), each tagged by its `kind` and deduplicated. The agent keeps them on the `ToolMessage` as plain JSON, so its memory of the turn holds no domain classes.

A turn whose tool or model fails (after the `model` node's `RetryPolicy` retries) ends with an `error` event carrying a user-facing message, never the exception. The agent does not remember the failed turn (its `memory` stays `None`), so the same message can be sent again. The chat shows a Retry button on that error while it is the last bubble.

## Errors

* Services raise an `AppError` subclass from `rag/domain/errors.py` with a `status_code`.
* One handler in `rag/app.py` turns every `AppError` into `{"detail": ...}`.
* `fastapi.HTTPException` is banned.

## Configuration

* Nested values use `__`: `LLM__API_KEY`, `RETRIEVAL__RERANK_CANDIDATES`.
* `LLM`, `OBSERVABILITY` and `KB_STORAGE` are discriminated unions on `BACKEND`.
