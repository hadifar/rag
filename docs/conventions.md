# Conventions — How to Extend This Codebase

Patterns to follow when adding to `rag/`, not a description of what already exists (that's
[reference.md](reference.md)). Each of these is already established by existing code — follow the
existing example rather than inventing a new shape.

## Coding style

Follows PEP 20 and the
[Google Python Style Guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md).

## Adding a new service or adapter: extend `container.py`, don't reach around it

`container.py` is the only place concrete adapters get constructed and injected — pure wiring, no
FastAPI/React imports. It's an async context manager so connections it opens (Pinecone, Postgres)
get torn down deterministically:

```python
@dataclass
class Container:
    ranking_service: RetrievalService
    generation_service: GenerationService
    ingestion_service: IngestionService


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container]: ...
```

A new adapter or service is wired in here, not constructed ad hoc inside a router or another
service. Routers and services never import `rag.adapters` directly — they take a `domain.ports`
`Protocol` in their constructor, and `container.py` is what supplies the concrete instance. This
is enforced by `import-linter`, not just convention — see
[enforcement.md](enforcement.md#python-code-quality).

## Adding a new ingestion source: implement a port, don't branch on source type

```python
class DocumentLoaderPort(Protocol):
    def load(self) -> Iterable[RawDocument]: ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Document]: ...
```

`MarkdownFileLoader` is the only concrete loader today. Adding a new source (PDF, Confluence, a
wiki) means writing a new class satisfying `DocumentLoaderPort` and registering it in
`container.py` — `IngestionService`, chunking, and the vector store adapter stay untouched. Don't
add an `if source_type == ...` branch inside `IngestionService` itself; that defeats the point of
the port.

Chunkers follow the same rule: `WholeDocumentChunker` (wired in by default) and
`MarkdownHeaderChunker` both satisfy `ChunkerPort` and are interchangeable. A new chunking
strategy is a new class satisfying that `Protocol`, not a parameter threaded through existing
chunkers. Give new chunks deterministic ids (`f"{source_id}::{chunk_index}"`, the existing
convention) so re-running `rag ingest` upserts over old vectors instead of duplicating them.

## Adding a new tool for the generation graph: build it as a closure, not a module-level `@tool`

`generation_service`'s `search_kb` tool is built as a closure inside `tools.py`
(`build_search_tool(ranking_service)`), not a module-level `@tool` function. Follow that shape for
a new tool: a `build_*_tool(dependency)` closure, so the tool keeps getting its dependency via
constructor injection like every other service, rather than reaching for a global or
re-instantiating a client per call.

## Adding a new observability or checkpointer backend: extend the discriminated union

Both `adapters/observability.py`'s `open_trace_config` and `adapters/checkpointer.py`'s
`open_checkpointer` pick their concrete implementation by pattern-matching on a `Settings` field
that's a discriminated union (`OBSERVABILITY`, `CHECKPOINTER` — each backend is its own Pydantic
model, keyed by a `BACKEND` literal, populated straight from nested env vars like
`OBSERVABILITY__PUBLIC_KEY`), so callers never branch on backend themselves — they just call
`trace_config(name)` or use the checkpointer object. A new backend is a new model class in
`config.py` plus a new `case` in the adapter, not a new code path exposed to callers.

## Adding a new secret

- **Local dev**: add it to `.env` (gitignored) and read it through `Settings`
  (`pydantic-settings`). Don't read `os.environ` directly outside `config.py`.
- **Prod**: add it to Azure Key Vault and reference it from App Service's Application Settings as
  a Key Vault reference — never as a plain env var with the value inline. See
  [reference.md#secrets-management](reference.md#secrets-management) for how the existing secrets
  are wired, and [infra.md](infra.md) for applying the Bicep template that provisions Key Vault
  access.
