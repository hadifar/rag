# Reference — What Exists Today

As-built description of the current system: what's implemented and how it behaves. For diagrams
of how pieces connect, see [architecture.md](architecture.md). For rules to follow when
*extending* any of this, see [conventions.md](conventions.md).

## Tech stack

| Concern | Choice |
|---|---|
| Language | Python ≥3.12, managed with `uv` |
| Backend framework | FastAPI, LangChain `create_agent` (on LangGraph) |
| Frontend | React 19 + TypeScript + Vite, Tailwind CSS |
| Retrieval | Hybrid search in Postgres: `pgvector` (HNSW, cosine) + full-text (`tsvector`, GIN), fused by reciprocal rank; embeddings from the LLM provider (`text-embedding-3-*`) |
| Auth | JWT (access + refresh) via `pyjwt`, `argon2-cffi` password hashing, users in Postgres — see [Authentication](#authentication) |
| Observability | `logging` (default) or `langfuse` |
| Local dev | Docker Compose — `backend` (FastAPI/uvicorn; uploaded knowledge-base zips on the `kbuploads` volume), `frontend` (nginx serving the Vite build, proxying `/api/*`), `postgres` (checkpointer + users + conversations + knowledge base) |
| Prod deployment | Azure App Service for Containers; secrets via Azure Key Vault references (see [Secrets management](#secrets-management)); uploaded knowledge-base zips in Azure Blob Storage |
| Quality gates | `ruff` (incl. `PTH`), `pre-commit`, `import-linter`, `commitizen` — see [enforcement.md](enforcement.md) |

## Layout

```
rag/
├── __init__.py / __main__.py         # `python -m rag` entrypoint
├── cli.py                            # Typer: `rag serve`, `rag ingest`, `rag create-user`, `rag set-admin`, `rag prune-threads`
├── config.py                         # Settings (pydantic-settings)
├── container.py                      # composition root
├── app.py                            # FastAPI-specific only: lifespan, app.state, routers, error handling
│
├── domain/                           # zero imports — pure contracts + models
│   ├── models.py
│   ├── ports.py
│   └── errors.py                     # AppError subclasses, each carrying its own `status_code`
│
├── services/                         # business logic — depends only on domain/ports
│   ├── retrieval_service/
│   ├── ingestion_service/
│   ├── agent_service/                # the chat agent: graph, guards, tools, streaming
│   ├── completion_service/           # single-shot LLM completions outside a chat turn (titles)
│   ├── conversation_service/         # ownership, one empty draft per user, titles, paging, delete
│   └── auth_service/                 # hashing + JWT issuance/verification, via UserRepositoryPort
│
├── adapters/                         # concrete SDK clients — the only importers of 3rd-party SDKs
│   ├── llm_client.py
│   ├── checkpointer.py
│   ├── observability.py
│   ├── archive_store.py              # uploaded knowledge-base zips: local disk or Azure Blob (KB_STORAGE)
│   └── db.py                         # the app's Postgres pool (users, conversations, documents)
│
├── repository/                       # concrete persistence implementing a domain port — same
│   ├── user_repository.py            # composition-root-only rule as adapters/, just a distinct kind of infra
│   ├── conversation_repository.py
│   ├── document_repository.py        # knowledge-base documents + chunks: pgvector + full-text hybrid search
│   └── ingestion_run_repository.py   # one row per upload; at most one `running`
│
├── api/
│   ├── deps.py                       # `Annotated[T, Depends(...)]` aliases, incl. ContainerDep/AuthenticatedUserDep
│   ├── schema/                       # request/response DTOs, one module per feature (conversations.py, auth.py, ...)
│   └── routers/                      # conversations.py, health.py, auth.py, etc. — flat `router = APIRouter(...)`
│
migrations/                            # Alembic — `users`, `conversations`, `chunks` (+ `vector` extension), `documents`, no ORM models elsewhere
frontend/                              # repo root — separate Vite/React app
├── src/
│   ├── api/                          # chat.ts (SSE client), conversations.ts, settings.ts, auth.ts, kb.ts, ingestions.ts
│   ├── components/                   # layout/ (shell, sidebar, auth guard), chat/ (message list, composer, bubbles), settings/ (knowledge-base upload)
│   ├── context/                      # AuthProvider (session status + user), ConversationsProvider (sidebar list)
│   ├── hooks/                        # useChat (streaming + history loading), useAuth/useConversations (read the providers), useKbUpload (upload + run polling)
│   ├── utils/                        # pure helpers (conversation list updates, history → bubbles)
│   └── pages/                        # ui pages, incl. LoginPage
└── (Vite build served by nginx in Docker)

infra/                                 # Docker + Azure, no Python
├── docker/                            # *.Docker
└── azure/                             # main.bicep — see docs/infra.md
```

## Services

Five services, each with a narrow constructor. There is no separate embedding service:
`DocumentRepository` embeds chunks at ingest and queries at search time itself, with the
`Embeddings` model `adapters/llm_client.py`'s `build_embeddings` builds (same provider and
credentials as the chat model, always asked for 1536 dimensions to match the `chunks` table).

| Service | Responsibility | Depends on |
|---|---|---|
| `retrieval_service` | hybrid (vector + full-text) search, single-document lookup by `source_id`, readiness ping | `VectorStorePort` |
| `ingestion_service` | load → hash → chunk and embed only new/changed docs → replace them and drop missing ones in one transaction, source-agnostic; stores uploaded zips and tracks each upload as a run | `ChunkerPort`, `DocumentIndexPort`, `ArchiveStorePort`, `IngestionRunRepositoryPort` |
| `agent_service` | owns the `create_agent` graph (model ⇄ tools, topical/groundedness guard middleware), tool calls, streaming, tracing; reads/deletes a thread's history | `BaseChatModel`, `SearchPort` (= `retrieval_service`), checkpointer |
| `completion_service` | single-shot LLM completions outside any chat turn — currently conversation title generation, never raises | `BaseChatModel` |
| `conversation_service` | conversation ownership, one empty draft per user, fallback and generated titles, paging, delete; runs each turn through the agent service, titles via the completion service | `ConversationRepositoryPort`, `GenerationPort` (= `agent_service`), `CompletionPort` (= `completion_service`) |
| `auth_service` | password hashing, JWT issuance/verification, user creation | `UserRepositoryPort` |

`container.py`'s `build_container` is the composition root: an async context manager that opens
the Postgres pools and tracing, constructs every adapter, repository and service, and tears the
connections down on exit. `app.py` stores the result on `app.state`, where `ContainerDep` in
`api/deps.py` reads it.

Documents are read by `loaders.py`: `load_directory` (a directory of `.md` files) and
`load_archive` (a `.zip`, read in memory, with member-count and uncompressed-size caps);
`load_path` picks one. Both use the file's basename as `source_id`. The one `ChunkerPort` is
`WholeDocumentChunker`.

Ingestion makes the index match the source. The `documents` table holds each indexed document's
content hash. A re-run chunks and embeds only documents whose hash changed, and deletes documents
the source no longer has; `chunks` rows cascade from their `documents` row, so a document that
shrank leaves no stale chunks. `rag ingest --force` re-embeds everything (after changing the
embedding model or chunker). A source with no documents is refused rather than emptying the index.

Uploaded zips are kept by an `ArchiveStorePort` (`adapters/archive_store.py`), picked by
`KB_STORAGE__BACKEND`: `local` (`KB_STORAGE__DIR`, default `data/uploads`) or `azure_blob`
(`KB_STORAGE__ACCOUNT_URL` + `KB_STORAGE__CONTAINER`, authenticated with
`DefaultAzureCredential`). Each upload gets a new timestamp-prefixed name and nothing is
overwritten, so `rag ingest --latest` can always rebuild the index from the newest one.
`IngestionService.save_archive` validates a zip before storing it, so invalid ones are never kept.

## LLM provider

`adapters/llm_client.py`'s `build_llm(settings)` returns a `BaseChatModel`, picked by matching
on `Settings.LLM`, a discriminated union selected by `LLM__BACKEND`:

- `"openai"` — `ChatOpenAI`, requiring `LLM__API_KEY` / `LLM__MODEL`.
- `"azure_openai"` — `AzureChatOpenAI`, requiring `LLM__API_KEY` / `LLM__ENDPOINT` /
  `LLM__DEPLOYMENT` / `LLM__API_VERSION`.

Either backend also takes `LLM__TEMPERATURE` (default `0.2`) and `LLM__RETRY_ATTEMPTS` (default
`3`, tries per LLM call in agents and guards before the fallback). Retrieval and the guards are
tuned under `RAG__`: `RAG__TOP_K` (default `3`, passages per search) and `RAG__MAX_REVISIONS`
(default `1`, times the groundedness guard sends an answer back per turn).

[infra/azure/main.bicep](../infra/azure/main.bicep)'s `llmProvider` param selects between the two
at deploy time — see [docs/infra.md](infra.md) for the parameters each one needs.

`GenerationService` (in `agent_service`), `CompletionService` and everything downstream only ever see the generic `BaseChatModel`
interface, so neither know or care which backend is selected.

## Conversation state

A conversation is a row in the `conversations` table (`id`, `user_id`, `title`, `created_at`,
`updated_at`; `migrations/versions/0002_…`), owned by `ConversationService`. Its messages live in
the LangGraph checkpointer, whose thread id is the conversation's id:
- A new chat starts with `POST /api/conversations`, which returns the caller's one empty
  (untitled) conversation, creating it if needed; the client then sends messages to its id.
- A missing conversation and another user's are the same 404, so ids can't be probed; for the
  message stream it's checked before the stream starts.
- A conversation is untitled only while empty: its first message names it straight away (the
  trimmed message). As it sends that message, the client also calls
  `POST /api/conversations/{id}/title` (not waiting for the answer), and an LLM call renames it
  from that message.
- The server never reconstructs history from a request payload — the checkpointer loads/saves
  it, and `GET /api/conversations/{id}/messages` reads it back (each question with its final
  answer and sources; tool calls aren't replayed).

The checkpointer is built by `adapters/checkpointer.py`'s `open_checkpointer()` (an async
context manager, mirroring `adapters/db.py`'s `open_db_pool()`): an `AsyncPostgresSaver` over a
connection pool of its own on the app's `DATABASE_URL` (required). It's a separate pool from the
repositories' because the saver needs different connection settings (`dict_row`, autocommit, no
prepared statements). Both pools test a connection before handing it out and replace dead ones,
so a Postgres restart doesn't need a backend restart; `checkpointer.setup()` runs on connect
(idempotent schema migration). Its tables live in their own `langgraph` Postgres schema (the pool
connects with `search_path=langgraph`), apart from the Alembic-owned tables in `public`. Durable
across restarts and safe for multiple backend replicas.
There is deliberately no in-memory option: conversation rows always live in Postgres, so
in-memory messages would leave every conversation empty after a restart.

## Authentication

Self-hosted, not a third-party identity provider (Clerk/Auth0/Entra ID were considered and
rejected, mainly to avoid another external dependency, and because the project already runs
its own Postgres).

- **No public signup.** Accounts are created out-of-band via `rag create-user <email>` (prompts
  for a password, `argon2-cffi` hashed) — there's no `POST /register`.
- **Admins** — `users.is_admin` (`rag create-user --admin`, or `rag set-admin <email>
  [--revoke]` for an existing user) gates the knowledge-base upload (`/api/ingestions`); the
  frontend shows it only when `GET /api/auth/me` says `is_admin`.
- **Access token** — a short-lived JWT (`AUTH__ACCESS_TOKEN_EXPIRE_MINUTES`, default 15m), returned
  in the `POST /api/auth/login` response body, sent by the frontend as `Authorization: Bearer`
  and kept in memory only (`api/client.ts`, never `localStorage`). Every API call goes through
  `authFetch`, which on a 401 refreshes once (concurrent 401s share one refresh) and retries;
  if the refresh fails too, `AuthProvider` switches to unauthenticated and `RequireAuth`
  redirects to `/login`.
- **Refresh token** — a longer-lived JWT (`AUTH__REFRESH_TOKEN_EXPIRE_DAYS`, default 7d), set as an
  httpOnly/SameSite=Lax cookie scoped to `/api/auth`, always `Secure` (TLS
  terminates at nginx/App Service, so the app can't tell https from the request; local dev over
  `http://localhost` still works in Chrome/Firefox, not Safari).
  `POST /api/auth/refresh` reads it and issues a new access token — there's no rotation or
  revocation store, so a stolen refresh token stays valid until it naturally expires (see
  [limitation.md](limitation.md#security)).
- **Gating** — `get_current_user` (`api/deps.py`) is applied as a router-level dependency to
  `conversations`/`kb`/`settings`, and `get_current_admin` (403 for non-admins) to
  `ingestions`; `auth` and `health` stay open (health is a liveness/readiness probe hit
  by infra with no session — see [conventions.md](conventions.md)).
- **Storage** — a `users` table (`id`, `email`, `hashed_password`, `created_at`, `is_admin`) in the app's
  one Postgres database (`DATABASE_URL`); schema is a plain Alembic
  migration (`migrations/versions/0001_create_users_table.py`), not auto-created like the
  checkpointer's own `.setup()`.

## Streaming

`agent_service/streaming.py` normalizes LangGraph's `astream_events` into one small event
vocabulary (`TextDelta`, `ToolCall` — `status` `pending` with its `query`, then `done` with its `output` — and `SourcesReady`), filtered to the `model` node's chat
model calls only — the guard middleware runs its own LLM calls (classification, not an
answer) through the same graph, and `astream_events` would otherwise leak those tokens into the
text stream too. Two consumers read the normalized stream:
- FastAPI's `POST /api/conversations/{id}/messages` turns it into SSE: each event is one
  `data:` line of JSON told apart by `type` — `text`, `tool` (`status` `pending` with its
  `query`, then `done` with its `output`) and `sources`. The shapes are Pydantic models
  (`TextEvent`/`ToolEvent`/`SourcesEvent`), so they're in the OpenAPI schema and the frontend's
  generated types. JSON also keeps a token containing `\n\n` from ending the SSE event early.
- The React frontend consumes that SSE stream with `@microsoft/fetch-event-source`
  (`api/chat.ts`), rendering tool calls via `ToolBubble` and citations via `SourcesBubble`
  (which links to `/api/retrieval/{filename}`).

## Observability

`adapters/observability.py` exposes `open_trace_config(settings)`, an async context manager
(opened in `container.py` alongside the vector store and checkpointer) that yields a
`trace_config(name)` callable returning a LangChain `RunnableConfig` with the backend's callback
wired in — so callers always pass `config=trace_config(...)` with no behavioral branching.
`GenerationService` uses it to tag the chat run. The backend is a discriminated union,
`Settings.OBSERVABILITY`, selected by `OBSERVABILITY__BACKEND`:

- `"logging"` (default) — `_LoggingCallbackHandler` logs LLM/tool start/end events through the
  standard `logging` module; zero extra infra.
- `"langfuse"` — a single Langfuse `CallbackHandler`, requiring `OBSERVABILITY__PUBLIC_KEY` /
  `OBSERVABILITY__SECRET_KEY` / `OBSERVABILITY__HOST` (required fields on the `LangfuseObservabilityConfig`
  model in `config.py` — missing one fails at startup). On teardown, the context manager's
  `finally` calls `get_client().flush()` so short-lived runs aren't lost.

## Secrets management

**Local dev** — all secrets live in `.env` (gitignored, never committed), loaded by
`pydantic-settings`. The exception is the local `postgres` compose service, which uses fixed
throwaway credentials (`rag`/`rag`) hardcoded in `docker-compose.yml` and bound to `127.0.0.1`
only — it holds nothing worth protecting, and a real password would just have to be kept in sync
with `DATABASE_URL` by hand.

**Prod (Azure App Service)** — secrets are stored in Azure Key Vault and exposed to the app as
*Key Vault references* in App Service's Application Settings. App Service resolves these (via the
app's system-assigned Managed Identity — no credentials stored anywhere) into plain env vars
before the container starts, so `Settings` needs no code changes: it already reads config from
`os.environ` via `pydantic-settings`. Registry access (`AcrPull`/`AcrPush`) follows the same
no-stored-credentials pattern.

This whole setup — Key Vault, RBAC role assignments, App Service, Container Registry, and the VNet
+ Private Endpoint that keep the backend off the public internet (see [docs/infra.md](infra.md#infraazure))
— is codified in [infra/azure/main.bicep](../infra/azure/main.bicep); see
[docs/infra.md](infra.md) for how to validate, preview, and deploy it. Provision/update by
running that template, not by hand.

Known limitation: App Service caches resolved Key Vault references and refreshes them
periodically (not instantly), so rotating a secret's value in the Vault requires restarting the
app to pick it up immediately.

## API surface

`conversations`/`kb`/`settings` all require `Authorization: Bearer <access_token>` (see
[Authentication](#authentication)); `ingestions` additionally requires an admin (403 otherwise);
`auth` and `health` don't.

Errors: services raise `rag.domain.errors.AppError` subclasses, each with a `status_code`
class attribute (500 on the base). `app.py`'s `register_error_handlers` registers one
`@app.exception_handler(AppError)`, and Starlette's MRO-based dispatch sends every subclass
there, so the response status comes from the exception class itself.

- `POST /api/auth/login` — `{email, password}` → `{access_token, token_type}`, sets the refresh
  cookie.
- `POST /api/auth/refresh` — reads the refresh cookie → a new `{access_token, token_type}`.
- `POST /api/auth/logout` — clears the refresh cookie.
- `GET /api/auth/me` — returns `{id, email, is_admin}` for the caller's access token.
- `POST /api/conversations` — the caller's empty conversation `{id, title: null, created_at,
  updated_at}`: a new one, or the one they already have (a partial unique index allows one
  untitled conversation per user, so empty chats can't pile up).
- `POST /api/conversations/{id}/messages` — `{message: str}` → SSE stream of normalized events.
  A first message also names the conversation (the trimmed message). 404 for a missing or
  someone else's conversation, before the stream starts.
- `POST /api/conversations/{id}/title` — `{message: str}` → renames the conversation with an
  LLM-written title for that first message and returns it; keeps the current title if the LLM fails. 404 as above.
- `GET /api/conversations?limit=&cursor=` — the caller's conversations, most recently used first,
  as `{items, next_cursor}`; pass `next_cursor` back for the next page (`null` on the last).
- `GET /api/conversations/{id}/messages` — `[{role, text, sources}]`, or 404.
- `DELETE /api/conversations/{id}` — deletes its messages, then the conversation; 204, or 404.
- `GET /api/health/live` — always 200 (liveness probe).
- `GET /api/health/ready` — queries the `chunks` table (fails if Postgres is unreachable or
  the migrations haven't run); no embedding or LLM call, so probes cost nothing.
- `POST /api/ingestions` — multipart `file` (a `.zip` of `.md` files, ≤ 20 MB) → 202 with a
  `running` run `{id, status, started_at, finished_at, added, updated, unchanged, removed,
  error}`. The zip is validated (400) and stored before the response; the ingestion itself runs
  as a background task afterwards. 409 if another run is still going (a partial unique index
  allows one `running` row), 413 if too large.
- `GET /api/ingestions/{id}` — the run, for polling until `status` is `succeeded` or `failed`;
  404 if unknown.
- `GET /api/ingestions/latest` — the most recent run, or `null`.
- `GET /api/retrieval/{filename}` — returns the reassembled document as `text/plain`, or 404. Used by
  the frontend's source citations (fetched with the auth header and opened as a blob — a bare
  `<a href>` can't carry a bearer token).
- `GET /api/settings` — returns `{model, temperature, top_k}` for display in the UI, read from
  the configured `Settings`: `LLM__MODEL` (the deployment on Azure), `LLM__TEMPERATURE` and
  `RAG__TOP_K` — the same values generation and retrieval run with.
