# Limitations

Known gaps. None of these is addressed yet.

## Ingestion

* Uploads run as an in-process background task. A restart kills the run. Startup marks it failed.
* The startup sweep assumes a single backend instance.
* `rag ingest` ignores the one-run-at-a-time rule.
* `rag ingest --latest` uses the newest valid zip, not the newest successful one.
* `WholeDocumentChunker` stores a whole file as one chunk.
* Only markdown sources exist.
* Embeddings have no model version. Changing the embedding model mixes old and new vectors until `rag ingest --force`.
* The vector size is fixed at 1536 (migration `0003`). Only `text-embedding-3-*` fits.

## Retrieval

* Search scans every chunk: the vector score adds the text and summary similarities (`RETRIEVAL__SUMMARY_WEIGHT`), which the HNSW index on `embedding` can't serve, and the fusion ranks every chunk.
* Keyword ranking is `ts_rank_cd`, which doesn't weigh a word by how rare it is (no BM25): a match on a word in every document counts as much as one on a word in one document. Words go through the `english` text-search config, so they're stemmed and stopwords are dropped, and a code like `QX-7731` is split into `qx` and `-7731`.
* Keyword search can't answer "latest" or "newest": no chunk stores a date to sort by.
* A document's summary is parsed from its own markdown: the `# title`, the paragraph under it, and the other headings. A file without a `# title` gets no summary and is scored on its text alone.
* The LLM reranker (`RETRIEVAL__RERANK_CANDIDATES`) only sees the `RETRIEVAL__RETRIEVAL_CANDIDATES` passages the search found, so it can't recover a passage ranked below them. It scores each passage by its summary alone, and a passage with no summary is shown to it blank. If its call fails, the search order is kept.
* No retrieval evaluation set.

## Guardrails

* `OffTopicGuard` only instructs the model to decline an off-topic (`restrict`) message. Only `block` stops the request.
* Both guards fail open: if their LLM call fails, the message or answer passes.
* `GroundednessGuard` passes an answer with no `search_kb` call.
* Past `MAX_REVISIONS` (`rag/services/agent_service/agent.py`), an ungrounded answer ships.
* An answer after any tool call doesn't stream: it shows in one piece after the check.
* Saved preferences enter the system prompt in the user's own words.

## Conversations

* A failed title request leaves the conversation untitled. The next new chat reopens it.
* Paging by `(updated_at, id)` can repeat a conversation across pages.
* The agent's whole memory of the conversation goes to the LLM every turn. Long conversations can exceed the context window.
* Turns from before migration `0014` have no agent memory: the agent starts those conversations afresh.

## Frontend

* The Settings page Save button persists nothing.
* A preference saved in another tab shows only after a reload.

## Security

* No password reset and no email verification.
* No token rotation or revocation.
* Login rate limiting is per IP only (nginx).
* The backend image runs as root on a floating base image.

## Reliability

* `search_kb` has no retry: a failed search fails the turn (see [Streaming](architecture/backend.md#streaming)).
* The SSE stream has no `done` event.
* `ChatOpenAI` has no request timeout.
* `/api/health/ready` does not check the embedding API.

## Observability

* Only `AppError` has a handler. Other exceptions become a bare 500.
* No error tracking or alerting.

## Scalability

* `rag serve` runs one uvicorn worker.
* The App Service Plan has no autoscale rule.
* nginx rate limits are per replica.

## CI/CD

* No CI job runs the frontend tests.
* Integration tests, image builds and deploys are manual.
* A pushed image needs `az webapp restart`.

## Infrastructure

* The knowledge-base Storage Account keeps a public endpoint.
* `AzureBlobArchiveStore` has no automated test.
* Bicep does not provision Postgres.
* No Azure deploy step runs `alembic upgrade head`.
