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
* Routers never import `rag.domain`.
* Nothing in `rag/api` imports `rag.config`: the container hands it an `AppSettings`.
* `rag.shared` imports nothing else in `rag`.

## Services

`agent_service` is the only LangChain user. `Llm` (`llm.py`, an `LLMPort`) is the one holder of the model, with its tracing and `LLM__RETRY_ATTEMPTS` tries per call: it gives titles, reranking and the agent's guards single-shot structured generation. `RagAgent` (an `AgentPort`) is the agent, built on that `Llm`; `chat_service` runs it for a conversation's turn.

`retrieval_service` fetches the `RETRIEVAL__RETRIEVAL_CANDIDATES` best passages for the query. The search is hybrid, in one SQL query: a vector ranking of every chunk and a full-text ranking of the chunks matching any of the query's words (`content_tsv`, `ts_rank_cd`), fused by reciprocal rank (`1 / (60 + rank)` summed over both). With `RETRIEVAL__RERANK_CANDIDATES` above 0, it passes them to `LlmReranker`: one structured LLM call judges each passage's summary relevant or not, the irrelevant ones are dropped, and the first `RETRIEVAL__RERANK_CANDIDATES` of the rest are returned in the search order, with their search scores. If none is relevant, the search returns nothing and `search_kb` tells the agent so. At 0, `NoReranker` keeps the search order and every fetched passage is returned. If the reranker's call fails, the search returns the passages in their search order.

## Caching

Three caches in Postgres (`rag/repository/cache_repository.py`, `CachePort`), under the `CACHE__*` settings: a query's embedding (`CachedEmbeddings` wraps the embeddings, queries only), a search's reranked result (`RetrievalService`, by its normalized query), and the off-topic guard's verdict (`classify_input`, by its whole prompt, history included).

* Each row is keyed by the model that made it and a sha256 of its input, so a new model misses every older row. A search's key also holds the retrieval settings.
* The tables are `UNLOGGED`. Each entry lives `CACHE__*_TTL_DAYS`; each write deletes a batch of expired rows.
* A search keeps chunk ids, not text: a hit reads the chunks, leaving out any removed. Ingestion empties `search_cache` in the transaction that replaces the chunks.
* Nothing is cached from a failure: a fail-open verdict or an unreranked search is computed afresh next time.
* A cache that fails is a miss; it never fails the request. `CACHE__ENABLED=false` swaps every cache for `NoCache`.

## Chat agent

Diagrams: [Agent graph](../diagrams/agent-graph.md), [Chat turn](../diagrams/chat-turn.md).

* Free text a user types (a chat message) is a `UserText` field (`rag/api/schema/common.py`): `normalize_text` (`rag/shared/text_normalizer.py`) applies NFKC, drops control, invisible and bidi-override characters, and tidies whitespace before the length checks run.
* `RagAgent` (`rag/services/agent_service/agent.py`) is the agent: a LangGraph `StateGraph` with four nodes, `classify` → `model` ⇄ `tools`, then `verify`, and `stream()`, which runs it one turn at a time (`AgentTurn`, in `streaming.py`). The search tool is in `tools.py`; everything about skills (their tools, `/<name>` invocation) in `skills.py`; the prompts and `system_prompt` in `prompts.py`; what a turn saves and what later turns reread in `memory.py`; splitting a thread into turns in `messages.py`; attachment rendering in `attachments.py`; and the guards' checks are plain functions in `guards/`.
* `classify` (`guards/off_topic.py`) classifies each user message, with the two turns before it, as `allow`, `restrict` or `block`, against `OFF_TOPIC_SCOPE`. Restrict (off-topic): the `model` node adds `OFF_TOPIC_INSTRUCTION` and binds no tools. Block (injection, jailbreak, harmful): the turn ends before the model runs, the user gets `BLOCKED_MESSAGE`, and the agent does not remember the message. All three are in `rag/services/agent_service/prompts.py`.
* History: each turn's `memory` is saved whole (its messages from the question on, tool calls included), but the model rereads less of it. `recall` (`rag/services/agent_service/memory.py`) keeps each earlier turn's question, its final answer and any `load_skill` call and result, leaving out its searches (a later turn can search again). Then it drops the oldest turns, whole, until the rest are at most `LLM__HISTORY_MAX_TURNS` and fit `LLM__HISTORY_MAX_TOKENS` (counted approximately), whichever limit is reached first (`HistoryLimits`). A dropped turn's attachments are no longer sent either.
* Both guards get a structured verdict (a Pydantic schema) from their LLM call. A failed call passes the message or answer (fail open).
* Attachments: the user's message (`HumanMessage`) stores its attachments' ids in `additional_kwargs["attachment_ids"]`, never their content, so `agent_messages` stays small. The files themselves sit in `ChatState.attachments`: this turn's files plus those of earlier turns, which the chat service loads with `AttachmentRepositoryPort.list_sent`. Before each model call, `with_attachments` (`attachments.py`) adds each file's content after the message text: markdown as a text block inside `<attachment>` tags, images as image blocks. To support a new file type, add an `AttachmentKind` in `rag/services/attachment_service/kinds.py` and a renderer in `_RENDERERS` in `rag/services/agent_service/attachments.py`.
* The off-topic guard classifies the message together with its attachments. The attachments go after the prompt (`Llm.generate_structured(..., attachments=...)`), and their sha256 hashes are part of the verdict cache key.
* Skills: a user saves SKILL.md files, or `.zip`/`.skill` archives of one with reference files (`POST /api/skills`, `SkillService` in `rag/services/skill_service/`). Each is a `name`, a `description` and instructions, in `user_skills`, and its reference files' text by path, in `user_skill_files`. An archive is recognized by its content and unpacked in memory by `read_archive` (`archive.py`), which takes SKILL.md from the archive's top or its one folder, keeps only UTF-8 text files, and checks the declared sizes before reading anything. It reads through `rag/shared/zip_reader.py`, as the knowledge-base upload does: never extracted, dotfiles and `__MACOSX/` left out, each file read at most one byte past its cap. The graph runs with the turn's `RunContext` as its context. The `model` node loads the user's skills on the turn's first model call (`SkillsPort.list_for_user`, which the `SkillRepository` serves, kept in `ChatState.skills`) and lists each one's name and description in the system prompt (`SKILLS_INSTRUCTION`). The `load_skill` tool returns one skill's instructions, followed by the paths of its reference files (`loaded_skill`), looked up by the user id in the run's `RunContext`. The `read_skill_file` tool returns one reference file by skill name and path. `recall` keeps `load_skill` results in later turns but drops `read_skill_file` results. The off-topic path gets neither the list nor the tools. A question that starts with `/<name>` of one of the user's skills invokes it: the `invoke_skill` node (between `classify` and `model`) adds a `load_skill` call and its result to the thread (`skill_loaded` in `rag/services/agent_service/skills.py`), so the model starts with the skill loaded and later turns remember it. An unknown name is left as plain text.
* Model and effort: `RunContext` carries the user's `model` and `effort` (set by the chat service from `users`). `Llm.models` holds one chat model per name (`build_llms(settings)`); the `model` node binds the tools to the turn's model and its effort with `Llm.with_effort`. The guards, titles and reranker use `Llm.model`, the one for `DEFAULT_MODEL`, so the off-topic verdict cache stays keyed by one model.
* `verify` (`guards/groundedness.py`) checks each answer against this turn's `search_kb` results. Ungrounded: it sends the answer back, at most `MAX_REVISIONS` times. `AnswerGate` holds the answer back from the stream until the verdict, so a rejected answer never reaches the user.

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
* Only `rag/container.py` reads `Settings`: it hands each service its values, and the API layer an `AppSettings` (`rag/domain/models/settings.py`), the configuration users may see, with no secrets (`AppSettingsDep`, `GET /api/settings`).
* Upload limits are the `UPLOADS__*` settings (`rag/config/uploads.py`). The container passes each to its service, which rejects a larger file (413). A router takes its file as a domain `Upload` through `rag/api/uploads.py` (`ArchiveUpload`, `SkillUpload`, `AttachmentUpload`), which reads it no further than one byte past the same limit. nginx caps each upload's request body from the same env vars, plus room for the multipart framing (`infra/docker/upload-limits.envsh`), so `docker-compose.yml` and `infra/azure/main.bicep` set them for both the backend and the frontend, to the defaults (`tests/unit/test_upload_limits.py`). `GET /api/settings` returns them (`uploads`), for the frontend to check and word sizes by.
