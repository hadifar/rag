# Limitations — Production Readiness

## Data & ingestion
- `rag ingest` is a manual, one-shot CLI step — nothing triggers it on a doc change
- Re-ingesting never deletes vectors for removed source files
- `WholeDocumentChunker` puts an entire file into one record — no size-aware chunking for docs past the embedding model's input limit
- `MarkdownHeaderChunker` exists and is arguably the better default, but nothing wires it up — `container.py` hardcodes `WholeDocumentChunker`, so the better chunker is dead code with no way to select it
- Only local markdown is supported — no PDF, Confluence, wiki, etc. loaders
- No embedding-model versioning: changing `PINECONE_DENSE_MODEL`/`PINECONE_SPARSE_MODEL` leaves old vectors from the previous model silently mixed in with new ones, with no re-embed/migration path
- `ensure_indexes()` runs on every app boot (not just `rag ingest`), so the backend's Pinecone API key needs index-*creation* rights just to start serving traffic — broader than a request-serving process should need, and a bad fit for least-privilege

## Retrieval
- Single fixed Pinecone namespace — no per-tenant/workspace isolation
- No reranker
- Reciprocal rank fusion uses a hardcoded `k=5` (`_reciprocal_rank_fusion`) — untuned against any eval set; the conventional default is `k=60`, and this choice overweights whichever result lands rank 1
- `top_k` is hardcoded to 3 in `RetrievalService.search` and never threaded through — `/api/settings` reports `top_k: 4`, which isn't actually what retrieval uses
- No retrieval evaluation at all: no golden Q&A set, no precision/recall/groundedness metrics, nothing to catch a regression from a prompt, chunking, or model change before it ships

## Generation & guardrails
- The topical guardrail is advisory, not a gate: `guardrail → agent` is an unconditional edge (see `graph.py`), so an off-topic classification only injects a "please decline" `SystemMessage` — the main agent LLM can still be talked out of following it. There is no code path that actually blocks a request.
- The guardrail classifies only the latest human message in isolation (`_latest_human_message`) — a multi-turn conversation that gradually drifts off-topic or builds up a jailbreak across turns isn't caught, since only the most recent turn is scored.
- The groundness verifier fails open in two ways: (1) if the agent answers without calling `search_kb` at all — including because it was talked out of it — `is_grounded` short-circuits to `True` with nothing to check against; (2) past `MAX_VERIFY_ATTEMPTS` (currently 1), an ungrounded answer ships anyway rather than being blocked or flagged to the user.
- Both guardrail and verifier parse the classifier LLM's free-text reply with a substring check (`"UNGROUNDED" not in ...`, `"IRRELEVANT" not in ...`) instead of structured/constrained output — any reply that doesn't hit the exact expected word defaults to the permissive outcome.
- `ChatOpenAI` is constructed with no `temperature` — despite `/api/settings` reporting a specific value (0.2), generation actually runs at the provider default, so the reported and real behavior diverge, and runs aren't reproducible for eval purposes.
- `GET /api/settings` returns the full system prompt to any unauthenticated caller — free reconnaissance for anyone trying to jailbreak the guardrail/agent.

## Conversation & session state
- `thread_id` is a client-supplied free string with no ownership check
- The frontend never persists `thread_id` anywhere — it's a `crypto.randomUUID()` held only in a React ref (`useChat.ts`), regenerated on every remount. A page refresh (or new tab) orphans the conversation in the Postgres checkpointer with no way for the user to get back to it, even though the backend is built to persist it.
- The sidebar's conversation history (`Sidebar.tsx`) is hardcoded `MOCK_SESSIONS` with a `// TODO: replace with real sessions from the backend` — every user sees the same fabricated list of past chats, none of which are theirs or clickable into real history.

## Security
- No authentication on any endpoint (`/chat/stream`, `/kb/*`, `/ui`)
- Dockerfile runs as root, pins no specific base image version (`python:3.12-slim` floats to whatever patch Docker Hub currently serves), and is a single-stage build
- System prompt disclosure via `/api/settings` (see Generation & guardrails above)

## Reliability
- No retry/backoff around Pinecone calls (LLM calls already retry with a fallback, see `graph.py`) — `search_kb` has no error handling at all, so a transient Pinecone error propagates straight out of the graph mid-turn instead of degrading gracefully like the LLM path does
- `ChatOpenAI` has no request timeout configured — a hung upstream call can hold a worker (and its Postgres checkpointer connection) open indefinitely rather than failing into the retry/fallback path
- `/health/ready` does a real embed + hybrid-search round trip on every hit
- Guardrail + verifier each add a full extra LLM call per turn, with no way to disable either
- `ChatRequest.message` has no length limit — nothing stops a single request from being arbitrarily large, which fans out into every downstream LLM call in the turn

## Observability
- Zero application logging anywhere in `rag/` — no `logging` usage at all. The only signal on failure is whatever uvicorn/App Service captures by default, plus LangChain/LangGraph traces in Langfuse *if* `LANGFUSE_ENABLED=true`
- No error tracking or alerting (no Sentry or equivalent) — a production incident would be discovered by a user complaint, not by the system

## Scalability
- `cli.py`'s `serve()` calls `uvicorn.run(...)` with no `workers=` — the app always runs as a single process today, even though the Postgres checkpointer would actually support scaling out
- `main.bicep`'s App Service Plan has no autoscale rule or instance count set, so it defaults to a single instance regardless of load
- `ensure_indexes()` (see Data & ingestion) runs unguarded on every app boot — if multiple replicas cold-start at once against a not-yet-created index, nothing prevents a race on `create_index_for_model`
- nginx's `limit_req` rate limit is per-nginx-process, in-memory state — the moment the frontend itself scales to more than one instance, the "10 req/min" budget becomes per-replica, not global, silently multiplying the effective limit

## Testing & CI
- Unit tests (`tests/unit/test_app.py`) are pure wiring tests against stubs — no coverage of guardrail logic, groundness verification, chunking, retry/fallback behavior, or answer quality
- Integration tests only run on manual `workflow_dispatch` (`integration-tests.yml`) — never automatically on push/PR to `master`, so there is no CI gate at all on retrieval or generation correctness before merge
- CI builds and pushes images (`build-push.yml`) only on manual `workflow_dispatch` — merging to `master` doesn't build/push automatically
- Nothing deploys automatically either — `infra/azure/main.bicep` must be applied by hand (`az deployment group create`); no deploy gate in CI
- No continuous-deployment hook from the registry to the Web Apps — after pushing a new image, they need a manual `az webapp restart` to actually pull it

## Infra & deployment
- The Postgres server behind `DATABASE_URL` isn't provisioned by the Bicep template — still undecided whether that's Azure Database for PostgreSQL or something else
