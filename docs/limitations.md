# Limitations

Known gaps. None of these is addressed yet.

## Ingestion

* Uploads run as an in-process background task. A restart kills the run. It shows as failed up to a minute later, once its lease lapses.
* A run whose process stalls for over a minute without dying is failed, but its ingestion can still commit afterwards. The index then matches the archive while the run reads `failed`.
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
* The LLM reranker (`RETRIEVAL__RERANK_CANDIDATES`) only sees the `RETRIEVAL__RETRIEVAL_CANDIDATES` passages the search found, so it can't recover a passage ranked below them. It judges each passage by its summary alone, and a passage with no summary is shown to it blank; a relevant passage it judges irrelevant is dropped, and if it drops them all the agent answers that it doesn't know. It only filters: the passages it keeps stay in the search order. If its call fails, the search order is kept.
* No retrieval evaluation set.

## Attachments

* Only `.md`, `.png` and `.jpg` files can be attached. The limits are 200 KB per `.md`, 5 MB per image, and 3 files per message.
* Files are stored in Postgres as `bytea`. Nothing streams them: every upload and download is held whole in memory.
* Every turn reloads and resends all images sent earlier in the conversation, which costs tokens and makes long image-heavy chats more likely to exceed the context window.
* The chat model must accept image input.
* A file that is uploaded but never sent stays stored until someone runs `rag prune-attachments`. Nothing schedules it. Removing a file while it is still uploading leaves it behind in the same way.
* A share link's JSON includes each attachment's id, type and size. The shared page shows only the file name, and the content needs the owner's login.

## Skills

* A user can save up to 20 skills. The limit is checked before the insert, so two uploads at once can go past it.
* A SKILL.md can be up to 50 KB. A `.zip` or `.skill` archive can be up to 512 KB as uploaded, and hold up to 50 reference files of up to 100 KB each, 500 KB in all once unpacked. Reference files must be UTF-8 text. Images, PDFs and other binary files are rejected, and scripts are kept only as text the model can read, never run.
* Reference files are stored in Postgres as text, and an upload is held whole in memory while it is unpacked.
* A reference file read in one turn is not reread by later turns (`recall` drops it like a search). The model must read it again.
* Without a `/<name>` command, the model decides when to load a skill. A message invokes at most one skill.
* An off-topic (`off_topic`) message loads nothing, even the skill it invokes. The input guard checks the message with its `/<name>` command, so a style skill (`/tone ...`) can be judged off-topic.
* The input guard doesn't know about skills, so a request a skill covers can still be judged `off_topic` and get no tools.
* Nothing checks what a skill or its reference files ask for. The prompt only tells the model that its own rules come first. See [Security](#security).
* The chat shows a `load_skill` call as a generic tool bubble.

## Models

* The three models are fixed in code (`ModelName` in `rag/domain/models/agent/agent.py`) and in a check constraint (migration `0022`). Adding one takes a migration.
* The provider must serve all three. For Azure, deployments must be named `gpt-6-luna`, `gpt-6-astra` and `gpt-6-sol`; `infra/azure/main.bicep` doesn't provision them.
* All three are treated alike: either they all reason (`LLM__REASONING_EFFORT` set) or the effort is ignored for all.
* A new chat's picks live in the browser until its first message; leaving the page before that drops them.

## Guardrails

* The input guard only instructs the model to decline an `off_topic` message. Only `block` stops the request.
* The input guard fails open: if its LLM call fails, the message passes.
* Nothing checks an answer against the evidence: only the answer prompt keeps it grounded.
* Every on-topic turn costs a research call that only says "Done." before the answer call.

## Conversations

* A failed title request leaves the conversation untitled. The next new chat reopens it.
* Paging by `(updated_at, id)` can repeat a conversation across pages.
* Past `LLM__HISTORY_MAX_TURNS` or `LLM__HISTORY_MAX_TOKENS`, the agent forgets the oldest turns outright: nothing summarizes them. The budget is an approximate count and leaves out attachments, so a chat heavy with attachments can still exceed the context window.
* Turns from before migration `0014` have no agent memory: the agent starts those conversations afresh.

## Security

* No password reset and no email verification.
* No token rotation or revocation.
* Login rate limiting is per IP only (nginx).
* Share links (`GET /api/shares/{share_id}`) are public, never expire, and have no rate limit. Shared answers can quote the knowledge base.
* The backend image runs as root on a floating base image.
* Uploaded skills are untrusted instructions. A skill, or a reference file it loads, goes to the model as instructions, and nothing scans it. A skill downloaded from elsewhere can carry prompt injection the user never read: it can tell the model to ignore the knowledge base, misstate facts, or answer with links to an outside URL that carry conversation text (answers render as markdown; nginx's CSP, `img-src 'self' data:`, blocks outside images, but a link only needs a click). Its reach is the user's own conversations and tools (`search_kb`), as with a message they type. The only safeguards are the system prompt (its rules come first) and a warning in Settings to upload only skills the user has read. Skills are never run, shared or shown to other users.

## Reliability

* `search_kb` has no retry: a failed search fails the turn (see [Streaming](architecture/backend.md#streaming)).
* The SSE stream has no `done` event.
* `ChatOpenAI` has no request timeout.
* `/api/health/ready` does not check the embedding API.

## Observability

* An unexpected exception answers a generic 500 with no error ID, so a user cannot point to its log entry.
* No alerting.
* Application Insights samples 25% of request traces, and stops taking data for the rest of the day past 0.16 GB. Postgres queries are not traced.
* A 4xx `AppError` (such as 401 or 404) is logged at INFO and not exported, so Application Insights sees it only on a sampled request trace.

## Scalability

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
