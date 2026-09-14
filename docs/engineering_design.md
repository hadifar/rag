# Engineering Design — RAG Chatbot

A retrieval-augmented chatbot over a static markdown knowledge base (`~/data/`), designed for clear
service boundaries and long-term maintainability rather than the shortest path to a demo.

## Guiding principles

- **Zen of Python (PEP 20), applied at the architecture level, not just line-by-line.**
  "Explicit is better than implicit" → dependencies are passed in via typed constructors, never
  reached for through globals or hidden imports. "Simple is better than complex" → four services,
  four ports, no framework abstractions adopted speculatively. "There should be one obvious way to
  do it" → one composition root (`container.py`) builds every object graph; nothing is wired twice.
- **Dependency inversion at every service boundary.** Business logic depends on `Protocol`
  interfaces (`domain/ports.py`), never on a concrete SDK. Concrete clients are swappable without
  touching a service.
- **YAGNI over speculative generality.** A few things were deliberately *not* built now (see
  "Explicitly deferred" below) because nothing in this project's actual scope needs them yet — the
  seams to add them later already exist.

## Tech stack

| Concern | Choice |
|---|---|
| Language / runtime | Python ≥3.12, managed with `uv` |
| Web framework | FastAPI (`/chat/stream`, health endpoints) |
| UI | Gradio, mounted onto the FastAPI app (`gr.mount_gradio_app`) |
| Orchestration | LangGraph |
| LLM + embeddings | `langchain-openai` — `ChatOpenAI` (`gpt-4o-mini`), `OpenAIEmbeddings` (`text-embedding-3-small`, 1536-dim) |
| Vector store | Pinecone via `langchain-pinecone` |
| Config | `pydantic` + `pydantic-settings` (defaults in code, `.env` overrides) |
| CLI | Typer (`rag.cli:app`) |
| Deployment | Docker → Azure Container Apps (serve) / Container Apps Jobs (ingest) |
| Quality gates | `ruff` (incl. `PTH`), `pre-commit`, `import-linter`, `commitizen` |

## Layout

```
rag/
├── __init__.py / __main__.py         # `python -m rag` entrypoint
├── cli.py                            # Typer: `rag serve`, `rag ingest`
├── config.py                         # Settings (pydantic-settings)
├── container.py                      # composition root — builds the object graph only
├── app.py                            # FastAPI-specific only: routes, Gradio mount
│
├── domain/                           # zero framework imports — pure contracts + models
│   ├── models.py                     # RawDocument, Chunk, RetrievedChunk, ChatTurn, Citation
│   └── ports.py                      # VectorStorePort, EmbedderPort, LLMPort,
│                                      # DocumentLoaderPort, ChunkerPort
│
├── services/                         # business logic — depends only on domain/ports
│   ├── embedding_service/
│   ├── ranking_service/
│   ├── ingestion_service/            # + loaders.py, chunking.py
│   └── generation_service/           # + graph.py, state.py, prompts.py, tools.py, streaming.py
│
├── adapters/                         # concrete SDK clients — the only importers of 3rd-party SDKs
│   ├── pinecone_client.py
│   ├── embedding_client.py
│   ├── llm_client.py
│   └── logging.py
│
├── api/
│   ├── schema.py                     # request/response DTOs
│   └── routers/                      # chat.py, health.py
│
└── ui/
    └── gradio_app.py

infra/                                 # repo root — Docker + Azure, no Python imports
├── docker/Dockerfile
└── azure/containerapp.bicep
```

Enforced by `import-linter` (`pyproject.toml`):
- `domain` imports nothing else in the project.
- `services` never imports `adapters` directly — only via injected `Protocol` types.
- Layering: `api | ui` → `services` → `domain`, one direction only.

## Services

Four services, each with a narrow, ports-typed constructor:

| Service | Responsibility | Depends on |
|---|---|---|
| `embedding_service` | `embed_query` / `embed_documents` | `EmbedderPort` |
| `ranking_service` | similarity search against the vector store | `VectorStorePort` |
| `ingestion_service` | load → chunk → embed → upsert, source-agnostic | `DocumentLoaderPort`, `ChunkerPort`, `EmbedderPort`, `VectorStorePort` |
| `generation_service` | owns the LangGraph graph; retrieve → generate, tool calls, streaming | `LLMPort`, `ranking_service` |

`RerankerPort` was considered and **dropped** — see "Explicitly deferred."

### `langchain-pinecone` reconciliation

`CLAUDE.md` specifies `langchain-pinecone`, which bundles a vector store's embedding step and its
similarity search behind one `VectorStore` interface, rather than treating them as fully separate
steps. The design keeps `EmbedderPort`/`EmbeddingService` as an explicit port — still backed by the
same `OpenAIEmbeddings` instance — but `adapters/pinecone_client.py`'s `VectorStorePort`
implementation wraps `langchain_pinecone.PineconeVectorStore`, constructed with that embeddings
object, and `VectorStorePort.query(text, top_k)` takes raw query text (delegating to
`asimilarity_search`) rather than a pre-computed vector. This keeps the embedding *provider* still
swappable at the `EmbeddingService` seam, while the query path stays idiomatic to
`langchain-pinecone` instead of fighting its abstraction.

## Dependency injection

`container.py` is the only place concrete adapters get constructed and injected — pure wiring, no
FastAPI/Gradio imports:

```python
@dataclass
class Container:
    embedding_service: EmbeddingService
    ranking_service: RankingService
    generation_service: GenerationService
    ingestion_service: IngestionService

def build_container(settings: Settings) -> Container: ...
```

`app.py`'s `create_app(container: Container | None = None) -> FastAPI` consumes an already-built
container — this also means tests can pass a `Container` of fakes into a real `FastAPI` app without
touching `Settings` or any network.

## Conversation state

LangGraph's `MemorySaver` checkpointer, keyed by a client-generated UUID `thread_id`:
- Gradio generates one per browser session (`gr.State`).
- A raw API caller generates and passes its own in `ChatRequest.thread_id`.
- The server never reconstructs history from a request payload — the checkpointer loads/saves it.
- Known limitation, accepted for now: in-memory state doesn't survive a restart or multiple
  replicas. Swapping to a persistent checkpointer (e.g. `langgraph-checkpoint-postgres`) later is a
  one-line change in `build_checkpointer()`, isolated to that adapter.

## Tool calling

`generation_service`'s `search_kb` tool is built as a closure inside `GenerationService.__init__`
(a `build_search_tool(self._ranking_service)` factory), not a module-level `@tool` function — this
keeps it consistent with constructor injection everywhere else, since `ranking_service` is a fixed
dependency of the service instance, not something that varies per request.

## Streaming

`generation_service/streaming.py` normalizes LangGraph's `astream_events` into one small event
vocabulary (`TextDelta`, `ThinkingDelta`, `ToolCallStart`, `ToolCallResult`). Both consumers read the
same async stream directly:
- FastAPI's `/chat/stream` turns it into SSE.
- Gradio's `ChatInterface.fn` is an `async def ... yield` generator — Gradio 6.x supports async
  generators natively (`inspect.isasyncgenfunction`), so no sync/async bridge is needed. Tool calls
  and thinking render via Gradio's `metadata={"title": ...}` collapsible-block convention.

## Ingestion — designed for more sources later

```python
class DocumentLoaderPort(Protocol):
    def load(self) -> Iterable[RawDocument]: ...

class ChunkerPort(Protocol):
    def chunk(self, doc: RawDocument) -> list[Chunk]: ...
```

`MarkdownFileLoader` is the only concrete loader today. Adding a new source (PDF, Confluence, a
wiki) means writing a new class satisfying `DocumentLoaderPort` and registering it — `IngestionService`,
chunking, embedding, and the vector store adapter are all untouched. Chunk IDs are deterministic
(`f"{source_id}::{chunk_index}"`), so re-running `rag ingest` after a doc changes updates existing
vectors instead of duplicating them. The Pinecone index is created idempotently (check-exists /
create-if-missing, dimension derived from the embedding model) on first `rag ingest` run — no manual
console step required.

## API surface

- `POST /chat/stream` — `{message: str, thread_id: str}` → SSE stream of normalized events.
- `GET /health/live` — always 200 (liveness probe).
- `GET /health/ready` — cheap Pinecone connectivity check + confirms LLM config is present, no real
  LLM call (readiness probe) — matches how Azure Container Apps probes work.

Auth/rate-limiting: **out of scope** for this build. `Settings` carries an unused optional `api_key`
field as a seam so a minimal API-key check can be added later without redesigning `api/`.


## Explicitly deferred (with rationale, not oversight)

| Item | Why deferred | Re-add path |
|---|---|---|
| `RerankerPort` | 28 short markdown docs — plain top-k similarity is very likely sufficient; a reranker adds latency/cost for dubious benefit at this corpus size | Same seam as `VectorStorePort`; add the port + adapter behind `ranking_service` if retrieval quality needs it |
| Automated tests | Out of scope for this build's timeline | Ports/DI already make every service testable with fakes — `tests/` mirroring `rag/`, `pytest` + `pytest-asyncio`, whenever added |
| Auth / rate limiting | Out of scope for this build | `Settings.api_key` seam already reserved |
| Persistent checkpointing | `MemorySaver` is sufficient for single-replica/demo scope | One-line swap in `build_checkpointer()` |
