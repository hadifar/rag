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
    auth_service: AuthService


@asynccontextmanager
async def build_container(settings: Settings) -> AsyncGenerator[Container]: ...
```

A new adapter or service is wired in here, not constructed ad hoc inside a router or another
service. Routers and services never import `rag.adapters` (or `rag.repository` — see
[below](#adding-a-new-repository-persistence-behind-a-domain-port)) directly — they take a
`domain.ports` `Protocol` in their constructor, and `container.py` is what supplies the concrete
instance. This is enforced by `import-linter`, not just convention — see
[enforcement.md](enforcement.md#python-code-quality).

## Adding a new repository: persistence behind a domain port

Same rule as adapters — `rag.repository` gets the same composition-root-only treatment as
`rag.adapters` in `import-linter` — but it's a distinct package because it's a distinct kind of
infra: `adapters/` wraps a third-party SDK client (Pinecone, an LLM provider); `repository/` holds
hand-written SQL over the project's own Postgres, implementing a domain port
(`UserRepositoryPort`, in `PostgresUserRepository`). Follow `user_repository.py`'s shape for a new
one: plain parameterized queries via `psycopg`'s `class_row(YourModel)` row factory (maps a row
straight onto the domain dataclass), no ORM — this project uses SQLAlchemy only as Alembic's
migration engine, never as an app-level ORM (see [limitation.md](limitation.md) if that
trade-off ever stops making sense for a new table's shape). Wire it into `container.py` like any
other adapter, injected into its service through the port, never imported by the service directly.

## Adding a new implementation of an existing capability: satisfy the `Protocol`, don't branch on type

Whenever code needs to support a new variant of something it already does — a new ingestion
source, a new chunking strategy, a new tool, a new anything — the fix is a new class satisfying an
existing (or new) `Protocol` in `rag.domain.ports`, wired into `container.py` (see above). It is
never an `if kind == ...` / `isinstance(...)` branch inside the code that *consumes* the
capability — that branch is the signal the abstraction is being bypassed rather than extended.

```python
class DocumentLoaderPort(Protocol):
    def load(self) -> Iterable[RawDocument]: ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Document]: ...
```

Concretely: `MarkdownFileLoader` is the only `DocumentLoaderPort` today. Adding a new source (PDF,
Confluence, a wiki) means writing a new class that satisfies `DocumentLoaderPort` and registering
it in `container.py` — `IngestionService`, chunking, and the vector store adapter stay untouched.
`WholeDocumentChunker` (wired in by default) and `MarkdownHeaderChunker` both satisfy `ChunkerPort`
the same way; a new chunking strategy is a new class satisfying that `Protocol`, not a parameter
threaded through existing chunkers. Give new chunks deterministic ids
(`f"{source_id}::{chunk_index}"`, the existing convention) so re-running `rag ingest` upserts over
old vectors instead of duplicating them.

The LLM/observability/checkpointer backends below follow the same rule through a different
mechanism — a discriminated union matched in one place instead of a `Protocol` — but the constraint
is identical: nothing downstream branches on which concrete implementation is active.

## Adding a new API route: thin router, `Annotated` deps, domain errors

Every router in `rag/api/routers/` follows the same shape: a flat, module-level
`router = APIRouter(prefix="/api/x", tags=["x"])`, with each endpoint a plain `@router.get`/`post`
function — not a `build_*_router()` factory wrapping closures. Handlers take their dependencies as
`Annotated[T, Depends(...)]` aliases from `deps.py` (`ContainerDep`, `RankingServiceDep`,
`SettingsDep`, `CurrentUserDep`, ...), never construct a service inline, and return/raise typed
Pydantic models — `Response` subclasses (`PlainTextResponse`, `StreamingResponse`) only when the
body genuinely isn't JSON. Business logic (retrieval, generation, chunk reassembly) lives in the
injected service, not in the route body — a route should read as "call the service, shape the
result." `app.py` imports the router object directly (`from rag.api.routers.chat import router as
chat_router`) and does `app.include_router(chat_router, dependencies=...)` — the prefix lives on
the router itself, not at inclusion time; `dependencies=` at inclusion time is for a uniform gate
across every route in that router (e.g. `[Depends(get_current_user)]` on `chat`/`kb`/`settings`);
a single route needing something the others don't takes it as a per-route dependency instead
(`@router.get(..., dependencies=[Depends(...)])` or a real parameter if the value is used, like
`auth.py`'s `/me` using `current_user: CurrentUserDep`).

`SettingsDep`/`get_app_settings` reads `request.app.state.settings` (`api/deps.py`) — the same
`app.state` pattern `ContainerDep`/`get_container` already uses — rather than FastAPI's
`dependency_overrides`, which is for tests reaching into an already-built app from the outside,
not for the app's own composition root to configure its routes.

On failure, raise a `rag.domain.errors.RagError` subclass, not `fastapi.HTTPException` — the
router doesn't know the right HTTP status for a domain failure. Give the new exception class a
`status_code: ClassVar[int]` in `rag/domain/errors.py` (defaults to 500 on the `RagError` base if
omitted); `rag/api/error_handlers.py`'s single `@app.exception_handler(RagError)` handler reads
`exc.status_code` polymorphically via Starlette's MRO-based dispatch, so a new domain error needs
no change to `app.py` or `error_handlers.py` at all — just the `status_code` on the new class.

## Adding a new schema/DTO

`rag/api/schema/` mirrors `rag/api/routers/` one module per feature (`chat.py`, `auth.py`,
`settings.py`, `health.py`) rather than one flat file — a new feature gets its own schema module,
imported only by its own router. These are request/response DTOs for the wire format, not domain
models — they live under `rag/api/` (not a top-level `rag/schema/`) because nothing outside
`rag.api` ever imports them; promoting them to a sibling of `domain`/`services`/`adapters` would
claim a cross-layer role they don't have, and `import-linter`'s `layering` contract already keeps
`domain`/`services` from reaching into `rag.api` at all, so nesting gets that boundary for free
instead of needing a new contract to state it.

## Adding a new closure-based dependency (a tool, a callback, any injected callable): close over it, don't reach for a global

Anything that needs a dependency at call time but isn't itself a class with a constructor — a
LangChain tool, an event callback, a handler passed to a library — takes the dependency the same
way a class would: as a parameter, captured once. `generation_service`'s `search_kb` tool follows
this shape (`build_search_tool(ranking_service)` in `tools.py`, not a module-level `@tool`
function). Follow it for anything similar: a `build_*(dependency) -> callable` closure, assembled
wherever its owning service is built, never a module-level global and never a client
re-instantiated per call.

## Adding a new backend behind a `Settings`-driven choice: extend the discriminated union, don't branch downstream

Whenever a capability's concrete implementation should be selected by configuration rather than by
call site — today: `LLM`, `OBSERVABILITY`, `CHECKPOINTER` — it's modeled as a discriminated union
in `config.py` (each backend its own Pydantic model, keyed by a `BACKEND` literal, populated
straight from nested env vars like `OBSERVABILITY__PUBLIC_KEY`), resolved by a single `match` in
the corresponding adapter (`adapters/llm_client.py`'s `build_llm`, `adapters/observability.py`'s
`open_trace_config`, `adapters/checkpointer.py`'s `open_checkpointer`). Callers never branch on
which backend is active — they just call `trace_config(name)`, use the checkpointer object, or (for
`LLM`) get back a plain `BaseChatModel`. A new backend is a new model class in `config.py` plus a
new `case` in that one `match`, not a new code path exposed to callers.

## Adding a new secret

- **Local dev**: add it to `.env` (gitignored) and read it through `Settings`
  (`pydantic-settings`). Don't read `os.environ` directly outside `config.py`.
- **Prod**: add it to Azure Key Vault and reference it from App Service's Application Settings as
  a Key Vault reference — never as a plain env var with the value inline. See
  [reference.md#secrets-management](reference.md#secrets-management) for how the existing secrets
  are wired, and [infra.md](infra.md) for applying the Bicep template that provisions Key Vault
  access.
