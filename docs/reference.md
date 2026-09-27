# Reference — What Exists Today

As-built description of the current system: what's implemented and how it behaves. For diagrams
of how pieces connect, see [architecture.md](architecture.md). For rules to follow when
*extending* any of this, see [conventions.md](conventions.md).

## Tech stack

| Concern | Choice |
|---|---|
| Language | Python ≥3.12, managed with `uv` |
| Backend framework | FastAPI, LangGraph |
| Frontend | React 19 + TypeScript + Vite, Tailwind CSS |
| Retrieval | Hybrid search via the `pinecone` SDK's async client directly — Pinecone hosts the embedding models |
| Auth | JWT (access + refresh) via `pyjwt`, `argon2-cffi` password hashing, users in Postgres — see [Authentication](#authentication) |
| Observability | `logging` (default) or `langfuse` |
| Local dev | Docker Compose — `backend` (FastAPI/uvicorn), `frontend` (nginx serving the Vite build, proxying `/api/*`), `postgres` (checkpointer + users storage) |
| Prod deployment | Azure App Service for Containers; secrets via Azure Key Vault references (see [Secrets management](#secrets-management)) |
| Quality gates | `ruff` (incl. `PTH`), `pre-commit`, `import-linter`, `commitizen` — see [enforcement.md](enforcement.md) |

## Layout

```
rag/
├── __init__.py / __main__.py         # `python -m rag` entrypoint
├── cli.py                            # Typer: `rag serve`, `rag ingest`, `rag create-user`
├── config.py                         # Settings (pydantic-settings)
├── container.py                      # composition root
├── app.py                            # FastAPI-specific only: lifespan, app.state, routers
│
├── domain/                           # zero imports — pure contracts + models
│   ├── models.py
│   ├── ports.py
│   └── errors.py                     # RagError subclasses, each carrying its own `status_code`
│
├── services/                         # business logic — depends only on domain/ports
│   ├── retrieval_service/
│   ├── ingestion_service/
│   ├── generation_service/
│   └── auth_service/                 # hashing + JWT issuance/verification, via UserRepositoryPort
│
├── adapters/                         # concrete SDK clients — the only importers of 3rd-party SDKs
│   ├── pinecone_client.py
│   ├── llm_client.py
│   ├── checkpointer.py
│   ├── observability.py
│   └── db.py                         # auth Postgres connection pool
│
├── repository/                       # concrete persistence implementing a domain port — same
│   └── user_repository.py            # composition-root-only rule as adapters/, just a distinct kind of infra
│
├── api/
│   ├── deps.py                       # `Annotated[T, Depends(...)]` aliases, incl. SettingsDep/CurrentUserDep
│   ├── error_handlers.py             # one handler, dispatches on each RagError's `status_code`
│   ├── schema/                       # request/response DTOs, one module per feature (chat.py, auth.py, ...)
│   └── routers/                      # chat.py, health.py, auth.py, etc. — flat `router = APIRouter(...)`
│
migrations/                            # Alembic — `users` table only, no ORM models elsewhere
frontend/                              # repo root — separate Vite/React app
├── src/
│   ├── api/                          # chat.ts (SSE client), settings.ts, auth.ts, kb.ts
│   ├── components/                   # ui component
│   ├── context/                      # AuthContext (access token in memory, refresh via httpOnly cookie)
│   ├── hooks/                        # hooks
│   └── pages/                        # ui pages, incl. LoginPage
└── (Vite build served by nginx in Docker)

infra/                                 # Docker + Azure, no Python
├── docker/                            # *.Docker
└── azure/                             # main.bicep — see docs/infra.md
```

## Services

Three services, each with a narrow, ports-typed constructor. There is no separate embedding
service — Pinecone's integrated inference embeds text server-side, so nothing in `rag/` ever
calls an embedding model directly.

| Service | Responsibility | Depends on |
|---|---|---|
| `retrieval_service` | hybrid (dense+sparse) similarity search, plus single-document lookup by `source_id` | `VectorStorePort` |
| `ingestion_service` | load → chunk → upsert, source-agnostic (upsert triggers Pinecone-side embedding) | `DocumentLoaderPort`, `ChunkerPort`, `VectorStorePort` |
| `generation_service` | owns the LangGraph graph: guardrail → agent → tools → verify, tool calls, streaming, tracing | `BaseChatModel`, `retrieval_service`, checkpointer |

## LLM provider

`adapters/llm_client.py`'s `build_llm(settings)` returns a `BaseChatModel`, picked by matching
on `Settings.LLM`, a discriminated union selected by `LLM__BACKEND`:

- `"openai"` — `ChatOpenAI`, requiring `LLM__API_KEY` / `LLM__MODEL`.
- `"azure_openai"` — `AzureChatOpenAI`, requiring `LLM__API_KEY` / `LLM__ENDPOINT` /
  `LLM__DEPLOYMENT` / `LLM__API_VERSION`.

[infra/azure/main.bicep](../infra/azure/main.bicep)'s `llmProvider` param selects between the two
at deploy time — see [docs/infra.md](infra.md) for the parameters each one needs.

`GenerationService` and everything downstream only ever see the generic `BaseChatModel`
interface, so neither know or care which backend is selected.

## Conversation state

A LangGraph checkpointer, keyed by a client-generated UUID `thread_id`, built by
`adapters/checkpointer.py`'s `open_checkpointer()` (an async context manager, mirroring
`open_vector_store()`) from `Settings.CHECKPOINTER`, a discriminated union selected by
`CHECKPOINTER__BACKEND`:
- The frontend generates one per browser session and passes it in every request.
- A raw API caller generates and passes its own in `ChatRequest.thread_id`.
- The server never reconstructs history from a request payload — the checkpointer loads/saves it.
- `"memory"` (default) → `InMemorySaver`, for local dev; doesn't survive a restart or multiple
  replicas.
- `"postgres"` → `AsyncPostgresSaver`, reading `CHECKPOINTER__DATABASE_URL`; `checkpointer.setup()`
  runs on connect (idempotent schema migration). Durable across restarts and safe for multiple
  backend replicas.

## Authentication

Self-hosted, not a third-party identity provider (Clerk/Auth0/Entra ID were considered and
rejected, mainly to avoid a second external dependency alongside Pinecone, and because the
project already runs its own Postgres).

- **No public signup.** Accounts are created out-of-band via `rag create-user <email>` (prompts
  for a password, `argon2-cffi` hashed) — there's no `POST /register`.
- **Access token** — a short-lived JWT (`AUTH__ACCESS_TOKEN_EXPIRE_MINUTES`, default 15m), returned
  in the `POST /api/auth/login` response body, sent by the frontend as `Authorization: Bearer`
  and kept in memory only (React context, never `localStorage`).
- **Refresh token** — a longer-lived JWT (`AUTH__REFRESH_TOKEN_EXPIRE_DAYS`, default 7d), set as an
  httpOnly/SameSite=Lax cookie scoped to `/api/auth`, always `Secure` (TLS
  terminates at nginx/App Service, so the app can't tell https from the request; local dev over
  `http://localhost` still works in Chrome/Firefox, not Safari).
  `POST /api/auth/refresh` reads it and issues a new access token — there's no rotation or
  revocation store, so a stolen refresh token stays valid until it naturally expires (see
  [limitation.md](limitation.md#security)).
- **Gating** — `get_current_user` (`api/deps.py`) is applied as a router-level dependency to
  `chat`/`kb`/`settings`; `auth` and `health` stay open (health is a liveness/readiness probe hit
  by infra with no session — see [conventions.md](conventions.md)).
- **Storage** — a `users` table (`id`, `email`, `hashed_password`, `created_at`) in the same
  Postgres instance the checkpointer uses, via `AUTH__DATABASE_URL`; schema is a plain Alembic
  migration (`migrations/versions/0001_create_users_table.py`), not auto-created like the
  checkpointer's own `.setup()`.

## Streaming

`generation_service/streaming.py` normalizes LangGraph's `astream_events` into one small event
vocabulary (`TextDelta`, `ToolCallStart`, `ToolCallResult`), filtered to the `agent` node's chat
model calls only — `guardrail` and `verify` run their own LLM calls (classification, not an
answer) through the same graph, and `astream_events` would otherwise leak those tokens into the
text stream too. Two consumers read the normalized stream:
- FastAPI's `POST /api/chat/stream` turns it into SSE (`text` / `tool_start` / `tool_result` /
  `sources` events). Every event's `data` is a single-line JSON object — including `text`
  (`{"text": ...}`), because a raw token containing `\n\n` would end the SSE event early.
- The React frontend consumes that SSE stream with `@microsoft/fetch-event-source`
  (`api/chat.ts`), rendering tool calls via `ToolBubble` and citations via `SourcesBubble`
  (which links to `/api/kb/{filename}`).

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
  `OBSERVABILITY__SECRET_KEY` / `OBSERVABILITY__HOST` (required fields on the `LangfuseObservability`
  model in `config.py` — missing one fails at startup). On teardown, the context manager's
  `finally` calls `get_client().flush()` so short-lived runs aren't lost.

## Secrets management

**Local dev** — all secrets live in `.env` (gitignored, never committed), loaded by
`pydantic-settings`. The one exception is the `postgres` container's own init password: it's
passed via a Docker Compose secret file (`.secrets/postgres_password.txt`, also gitignored,
referenced in `docker-compose.yml`'s `secrets:` block) rather than an env var, so it never has to
round-trip through `Settings` at all — the app connects to Postgres using
`CHECKPOINTER__DATABASE_URL`/`AUTH__DATABASE_URL` (both already contain the same password), not
`POSTGRES_PASSWORD`.

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

`chat`/`kb`/`settings` all require `Authorization: Bearer <access_token>` (see
[Authentication](#authentication)); `auth` and `health` don't.

- `POST /api/auth/login` — `{email, password}` → `{access_token, token_type}`, sets the refresh
  cookie.
- `POST /api/auth/refresh` — reads the refresh cookie → a new `{access_token, token_type}`.
- `POST /api/auth/logout` — clears the refresh cookie.
- `GET /api/auth/me` — returns `{id, email}` for the caller's access token.
- `POST /api/chat/stream` — `{message: str, thread_id: str}` → SSE stream of normalized events.
- `GET /api/health/live` — always 200 (liveness probe).
- `GET /api/health/ready` — deliberately exercises the real retrieval path (a dense+sparse
  Pinecone query) rather than a bare ping, so "ready" actually means "can serve"; no real LLM
  call.
- `GET /api/kb/{filename}` — returns the reassembled document as `text/plain`, or 404. Used by
  the frontend's source citations (fetched with the auth header and opened as a blob — a bare
  `<a href>` can't carry a bearer token).
- `GET /api/settings` — returns `{model, temperature, top_k}` for display in the UI.
  `temperature` and `top_k` are currently static constants in the router, not yet threaded
  through the actual generation/retrieval calls they name.
