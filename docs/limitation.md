# Limitations — Production Readiness

## Data & ingestion
- Uploads (`POST /api/ingestions`) run as an in-process background task: a backend restart
  mid-run kills it, and the next startup marks it failed, so the admin has to upload again
  (safe: the index is only swapped in one transaction at the end). That startup sweep assumes a
  single backend instance: with several, one restarting would mark another's live run failed
- `rag ingest` doesn't take part in the one-run-at-a-time rule — running it while an upload is
  being ingested can make one of the two fail (the other still completes)
- `rag ingest --latest` rebuilds from the newest *stored* upload, which is the newest *valid* zip
  but not necessarily one that ingested successfully (e.g. if embedding failed)
- `WholeDocumentChunker` puts an entire file into one record — no size-aware chunking for docs past the embedding model's input limit
- Only local markdown is supported — no PDF, Confluence, wiki, etc. loaders
- No embedding-model versioning: changing `LLM__EMBEDDING_MODEL`/`LLM__EMBEDDING_DEPLOYMENT` leaves old vectors from the previous model silently mixed in with new ones (same dimensions, different meaning) — unchanged documents are skipped on re-ingest, so nothing re-embeds them unless you remember `rag ingest --force`. The vector size itself is fixed at 1536 by migration `0003`, so only `text-embedding-3-*` models fit
- Every search makes one embedding API call, and every ingested chunk one embedding (batched) — retrieval now depends on the LLM provider being up, not just Postgres

## Retrieval
- The keyword side is Postgres full-text with the `english` configuration and `ts_rank_cd`, not BM25: no IDF weighting, and non-English documents are stemmed as English
- No reranker
- Reciprocal rank fusion uses a hardcoded `k=5` (`_reciprocal_rank_fusion`) — untuned against any eval set; the conventional default is `k=60`, and this choice overweights whichever result lands rank 1
- No retrieval evaluation at all: no golden Q&A set, no precision/recall/groundedness metrics, nothing to catch a regression from a prompt, chunking, or model change before it ships

## Generation & guardrails
- The topical guardrail is advisory, not a gate: an off-topic classification only adds a "please decline" instruction and removes the tools for that turn (`TopicalGuard`) — the model can still be talked out of following the instruction. There is no code path that actually blocks a request.
- The guardrail classifies only the latest human message in isolation (`_latest_human_message`) — a multi-turn conversation that gradually drifts off-topic or builds up a jailbreak across turns isn't caught, since only the most recent turn is scored.
- The groundness verifier fails open in two ways: (1) if the agent answers without calling `search_kb` at all — including because it was talked out of it — `is_grounded` short-circuits to `True` with nothing to check against; (2) past `RAG__MAX_REVISIONS` (default 1), an ungrounded answer ships anyway rather than being blocked or flagged to the user.
- Saved preferences go into the system prompt in the user's own words, so a user can put
  instructions there that the prompt only asks the model to rank below its own; it reaches
  only that user's chats, but it outlives the conversation it was said in.
- The model decides whether a message states a preference worth saving; it may miss one, or
  save one the user only implied, which they then have to ask it to forget.
- Both guardrail and verifier parse the classifier LLM's free-text reply with a substring check (`"UNGROUNDED" not in ...`, `"IRRELEVANT" not in ...`) instead of structured/constrained output — any reply that doesn't hit the exact expected word defaults to the permissive outcome.

## Conversation & session state
- The LLM title is a separate request the client makes once a new conversation's first answer
  has streamed (capped at 10s). If that request fails, times out or never happens (the tab was
  closed), the conversation keeps its fallback title, the trimmed first message; nothing retries.
- The sidebar paginates by `(updated_at, id)`, and using a conversation moves it to the top, so a
  conversation can reappear in a later page while scrolling; the frontend drops such duplicates,
  but a conversation used on another device meanwhile won't show up until a reload.
- Deleting a user cascades to their `conversations` rows but not to their LangGraph checkpoint
  threads or their preferences in the store, which live in separate tables with no user link — a full user deletion (GDPR) still
  has to delete each conversation's thread first.
- A thread whose conversation row was removed outside the app (e.g. a user deleted in SQL) is
  unreachable and stays in the checkpoint tables; nothing cleans these up.
- One database, two schema owners: Alembic owns the tables in `public`
  (`users`/`conversations`/`documents`/`chunks`/`ingestion_runs`), while LangGraph's
  checkpointer's and store's `setup()` create and migrate their own tables in the `langgraph`
  schema at every boot, outside Alembic's history.
- The whole thread is sent to the LLM every turn — no trimming or summarization — so long
  conversations get slower and costlier per turn and can eventually exceed the context window.
- The groundedness check runs after the answer has already streamed. When it asks for a
  revision, the user sees the rejected draft and the revision in the same bubble; reopening the
  conversation later shows only the revision.

## Frontend
- The Settings page's Save button only shows "Saved" — nothing is persisted (there's no write
  endpoint), which misleads users.

## Security
- Login/register are self-hosted, not a third-party identity provider — no self-serve signup
  (accounts are created out-of-band via `rag create-user`, an operational bottleneck as much as a
  security posture) and no password-reset/email-verification flow at all
- No refresh-token rotation or revocation store: `POST /api/auth/logout` only clears the client's
  refresh cookie — it doesn't invalidate anything server-side, so a captured access token stays
  valid until it naturally expires (`AUTH__ACCESS_TOKEN_EXPIRE_MINUTES`, default 15m), and a
  captured refresh token until `AUTH__REFRESH_TOKEN_EXPIRE_DAYS` (default 7d), with no way to cut
  either off early
- Login rate limiting is per IP only — `POST /api/auth/login` has its own nginx zone (5 req/min,
  burst 3), but nothing throttles failed attempts per account, so credential stuffing spread
  across many IPs, or a slow attack on one account, isn't slowed down
- Dockerfile runs as root, pins no specific base image version (`python:3.12-slim` floats to whatever patch Docker Hub currently serves), and is a single-stage build

## Reliability
- No retry/backoff around retrieval (LLM calls already retry with a fallback, see `graph.py`) — `search_kb` has no error handling at all, so a transient embedding-API or Postgres error propagates straight out of the graph mid-turn instead of degrading gracefully like the LLM path does
- The SSE stream has no `error` or `done` event: a failure mid-turn (e.g. the retrieval error above) just closes the connection, and the UI can only show a generic error
- `ChatOpenAI` has no request timeout configured — a hung upstream call can hold a request open indefinitely rather than failing into the retry/fallback path
- `/health/ready` only checks that the `chunks` table is queryable — it doesn't prove the embedding API works, so the backend can report ready while every search would fail
- Guardrail + verifier each add a full extra LLM call per turn, with no way to disable either

## Observability
- Almost no application logging: only the `logging` observability backend and a warning when title generation fails. `app.py`'s `register_error_handlers` only registers a handler for `AppError`, so any exception that isn't one becomes a bare 500 with nothing logged beyond uvicorn's default traceback, plus LangChain/LangGraph traces in Langfuse *if* `OBSERVABILITY__BACKEND=langfuse`
- No error tracking or alerting (no Sentry or equivalent) — a production incident would be discovered by a user complaint, not by the system

## Scalability
- `cli.py`'s `serve()` calls `uvicorn.run(...)` with no `workers=` — the app always runs as a single process today, even though the Postgres checkpointer would actually support scaling out
- Within one process, all checkpoint reads/writes run one at a time: `AsyncPostgresSaver` holds its own `asyncio.Lock` around every query, even with the connection pool `langgraph_persistence.py` now gives it (`AsyncPostgresStore` has its own lock too) (the pool is for reconnecting after a Postgres restart, not for concurrency). The queries are short and the lock isn't held during LLM calls, so this only matters at high request rates; more workers/replicas each get their own lock
- `main.bicep`'s App Service Plan has no autoscale rule or instance count set, so it defaults to a single instance regardless of load
- nginx's `limit_req` rate limit is per-nginx-process, in-memory state — the moment the frontend itself scales to more than one instance, the "10 req/min" budget becomes per-replica, not global, silently multiplying the effective limit

## Testing & CI
- Unit tests cover the guards' per-turn behavior (`test_generation_graph.py`, scripted fake model), `ConversationService`, `AuthService`, ingestion (archive loading, index sync, upload runs) and the API wiring against stubs — no unit coverage of the chunker, RRF, retry/fallback behavior, or answer quality
- Frontend tests (Vitest unit/integration, Playwright e2e) run only locally — no CI job runs them, so a frontend regression isn't caught before merge
- Integration tests only run on manual `workflow_dispatch` (`integration-tests.yml`) — never automatically on push/PR to `master`, so there is no CI gate at all on retrieval or generation correctness before merge
- CI builds and pushes images (`build-push.yml`) only on manual `workflow_dispatch` — merging to `master` doesn't build/push automatically
- Nothing deploys automatically either — `infra/azure/main.bicep` must be applied by hand (`az deployment group create`); no deploy gate in CI
- No continuous-deployment hook from the registry to the Web Apps — after pushing a new image, they need a manual `az webapp restart` to actually pull it

## Infra & deployment
- The knowledge-base Storage Account keeps a public endpoint (Entra ID/RBAC only, shared keys off): a private endpoint would also need the backend Web App VNet-integrated for outbound traffic, which only the frontend is today
- `AzureBlobArchiveStore` has no automated test (Azurite doesn't accept `DefaultAzureCredential`); its first real exercise is an upload on a deployed backend
- The Postgres server behind `DATABASE_URL` isn't provisioned by the Bicep template — still undecided whether that's Azure Database for PostgreSQL or something else
- No Azure deploy step runs `alembic upgrade head` against whatever Postgres ends up provisioned (Docker Compose does, via its one-off `migrate` service; the Azure equivalent would be a job running the same image with the same `alembic upgrade head` entrypoint, once per deploy)
