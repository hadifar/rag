# Limitations — Production Readiness

## Data & ingestion
- `rag ingest` is a manual, one-shot CLI step — nothing triggers it on a doc change
- Re-ingesting never deletes vectors for removed source files
- `WholeDocumentChunker` puts an entire file into one record — no size-aware chunking for docs past the embedding model's input limit
- `MarkdownHeaderChunker` exists and is arguably the better default, but nothing wires it up — `container.py` hardcodes `WholeDocumentChunker`, so the better chunker is dead code with no way to select it
- Only local markdown is supported — no PDF, Confluence, wiki, etc. loaders
- No embedding-model versioning: changing `PINECONE__DENSE_MODEL`/`PINECONE__SPARSE_MODEL` leaves old vectors from the previous model silently mixed in with new ones, with no re-embed/migration path
- `ensure_indexes()` runs on every app boot (not just `rag ingest`), so the backend's Pinecone API key needs index-*creation* rights just to start serving traffic — broader than a request-serving process should need, and a bad fit for least-privilege

## Retrieval
- Single fixed Pinecone namespace — no per-tenant/workspace isolation
- No reranker
- Reciprocal rank fusion uses a hardcoded `k=5` (`_reciprocal_rank_fusion`) — untuned against any eval set; the conventional default is `k=60`, and this choice overweights whichever result lands rank 1
- `top_k` is hardcoded to 3 in `RetrievalService.search` and never threaded through — `/api/settings` reports `top_k: 4`, which isn't actually what retrieval uses
- No retrieval evaluation at all: no golden Q&A set, no precision/recall/groundedness metrics, nothing to catch a regression from a prompt, chunking, or model change before it ships

## Generation & guardrails
- The topical guardrail is advisory, not a gate: an off-topic classification only adds a "please decline" instruction and removes the tools for that turn (`TopicalGuard`) — the model can still be talked out of following the instruction. There is no code path that actually blocks a request.
- The guardrail classifies only the latest human message in isolation (`_latest_human_message`) — a multi-turn conversation that gradually drifts off-topic or builds up a jailbreak across turns isn't caught, since only the most recent turn is scored.
- The groundness verifier fails open in two ways: (1) if the agent answers without calling `search_kb` at all — including because it was talked out of it — `is_grounded` short-circuits to `True` with nothing to check against; (2) past `MAX_VERIFY_ATTEMPTS` (currently 1), an ungrounded answer ships anyway rather than being blocked or flagged to the user.
- Both guardrail and verifier parse the classifier LLM's free-text reply with a substring check (`"UNGROUNDED" not in ...`, `"IRRELEVANT" not in ...`) instead of structured/constrained output — any reply that doesn't hit the exact expected word defaults to the permissive outcome.
- `ChatOpenAI` is constructed with no `temperature` — despite `/api/settings` reporting a specific value (0.2), generation actually runs at the provider default, so the reported and real behavior diverge, and runs aren't reproducible for eval purposes.

## Conversation & session state
- Titles are LLM-generated after a new conversation's first answer, so the stream stays open
  (after the answer is complete) for one more short LLM call, capped at 10s. If it fails or
  times out, the conversation keeps its fallback title (the trimmed first message).
- The sidebar paginates by `(updated_at, id)`, and using a conversation moves it to the top, so a
  conversation can reappear in a later page while scrolling; the frontend drops such duplicates,
  but a conversation used on another device meanwhile won't show up until a reload.
- Deleting a user cascades to their `conversations` rows but not to their LangGraph checkpoint
  threads, which live in separate tables with no user link — a full user deletion (GDPR) still
  has to delete each conversation's thread first.
- Conversations created before the `conversations` table existed (checkpoint threads keyed by
  the old client-generated `thread_id`) have no row, so they're unreachable, not migrated.
- Users/conversations (`AUTH__DATABASE_URL`, schema by Alembic) and messages
  (`CHECKPOINTER__DATABASE_URL`, schema by `checkpointer.setup()` at boot) are two settings and
  two schema owners for what is, in every deployment so far, the same database.
- The whole thread is sent to the LLM every turn — no trimming or summarization — so long
  conversations get slower and costlier per turn and can eventually exceed the context window.
- The groundedness check runs after the answer has already streamed. When it asks for a
  revision, the user sees the rejected draft and the revision in the same bubble; reopening the
  conversation later shows only the revision.

## Frontend
- The access token (15 min) is only refreshed on page load — after it expires every API call
  fails with 401 until the user reloads. Each `api/*.ts` module also does its own `fetch`,
  headers and error handling; there's no shared client that could refresh-and-retry once.
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
- No login-specific rate limiting — `POST /api/auth/login` only gets nginx's generic `limit_req`
  on all of `/api/*` (10 req/min per IP), not a tighter, brute-force-aware budget of its own
- Dockerfile runs as root, pins no specific base image version (`python:3.12-slim` floats to whatever patch Docker Hub currently serves), and is a single-stage build

## Reliability
- No retry/backoff around Pinecone calls (LLM calls already retry with a fallback, see `graph.py`) — `search_kb` has no error handling at all, so a transient Pinecone error propagates straight out of the graph mid-turn instead of degrading gracefully like the LLM path does
- The SSE stream has no `error` or `done` event: a failure mid-turn (e.g. the Pinecone error above) just closes the connection, and the UI can only show a generic error
- `ChatOpenAI` has no request timeout configured — a hung upstream call can hold a request open indefinitely rather than failing into the retry/fallback path
- `/health/ready` does a real embed + hybrid-search round trip on every hit
- Guardrail + verifier each add a full extra LLM call per turn, with no way to disable either

## Observability
- Almost no application logging: only the `logging` observability backend and a warning when title generation fails. `error_handlers.py` has no catch-all handler, so any exception that isn't a `RagError` becomes a bare 500 with nothing logged beyond uvicorn's default traceback, plus LangChain/LangGraph traces in Langfuse *if* `OBSERVABILITY__BACKEND=langfuse`
- No error tracking or alerting (no Sentry or equivalent) — a production incident would be discovered by a user complaint, not by the system

## Scalability
- `cli.py`'s `serve()` calls `uvicorn.run(...)` with no `workers=` — the app always runs as a single process today, even though the Postgres checkpointer would actually support scaling out
- Within one process, all checkpoint reads/writes run one at a time: `AsyncPostgresSaver` holds its own `asyncio.Lock` around every query, even with the connection pool `checkpointer.py` now gives it (the pool is for reconnecting after a Postgres restart, not for concurrency). The queries are short and the lock isn't held during LLM calls, so this only matters at high request rates; more workers/replicas each get their own lock
- `main.bicep`'s App Service Plan has no autoscale rule or instance count set, so it defaults to a single instance regardless of load
- `ensure_indexes()` (see Data & ingestion) runs unguarded on every app boot — if multiple replicas cold-start at once against a not-yet-created index, nothing prevents a race on `create_index_for_model`
- nginx's `limit_req` rate limit is per-nginx-process, in-memory state — the moment the frontend itself scales to more than one instance, the "10 req/min" budget becomes per-replica, not global, silently multiplying the effective limit

## Testing & CI
- Unit tests cover the guards' per-turn behavior (`test_generation_graph.py`, scripted fake model), `ConversationService`, and the API wiring against stubs — no coverage of chunking, RRF, retry/fallback behavior, or answer quality
- No frontend tests at all — `useChat`, the conversations context and the SSE parsing are only checked by `tsc`
- Integration tests only run on manual `workflow_dispatch` (`integration-tests.yml`) — never automatically on push/PR to `master`, so there is no CI gate at all on retrieval or generation correctness before merge
- CI builds and pushes images (`build-push.yml`) only on manual `workflow_dispatch` — merging to `master` doesn't build/push automatically
- Nothing deploys automatically either — `infra/azure/main.bicep` must be applied by hand (`az deployment group create`); no deploy gate in CI
- No continuous-deployment hook from the registry to the Web Apps — after pushing a new image, they need a manual `az webapp restart` to actually pull it

## Infra & deployment
- The Postgres server behind `CHECKPOINTER__DATABASE_URL` isn't provisioned by the Bicep template — still undecided whether that's Azure Database for PostgreSQL or something else
- `AUTH__DATABASE_URL`/`AUTH__JWT_SECRET` aren't wired into `main.bicep`/Key Vault at all yet. `AUTH` is a required setting, so a backend deployed from the current template fails `Settings` validation at boot — the Azure deploy is broken until this is wired. Same gap as the checkpointer's `CHECKPOINTER__DATABASE_URL` above, plus a deploy step to actually run `alembic upgrade head` against whatever Postgres ends up provisioned, which nothing automates today (`infra/docker/Dockerfile.backend` now ships `alembic.ini`/`migrations/` so it *can* run inside the container, but something still has to invoke it once per deploy)
