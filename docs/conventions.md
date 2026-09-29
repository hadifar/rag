# Conventions — How to Extend This Codebase

Patterns to follow when adding to this codebase. What already exists is described in
[reference.md](reference.md), and why it's shaped that way in [architecture.md](architecture.md).
Each pattern below has an existing example — copy its shape rather than inventing a new one.

## Coding style

Follows PEP 20 and the
[Google Python Style Guide](https://github.com/google/styleguide/blob/gh-pages/pyguide.md).

## Adding a new service or adapter: wire it in `container.py`

- Construct and inject it in `container.py`'s `build_container`, add it as a field on
  `Container`, and let the container close anything it opens.
- Never construct an adapter or service ad hoc inside a router or another service.
- Routers and services never import `rag.adapters` or `rag.repository`, and services never
  import each other — they take a `rag.domain.ports` `Protocol` in their constructor (e.g.
  `SearchPort` for the knowledge-base search generation needs), and `container.py` supplies the
  concrete instance. `import-linter` enforces this
  ([enforcement.md](enforcement.md#python-code-quality)).

## Adding a new repository: SQL behind a domain port

- Put it in `rag/repository/`, implementing a `Protocol` from `rag.domain.ports` (example:
  `UserRepositoryPort` → `rag/repository/user_repository.py`), and wire it in `container.py`.
- `adapters/` is for wrapped third-party SDK clients
  instead.
- Schema changes go in a new Alembic revision under `migrations/versions/`; a committed
  migration is never edited (the `migrations-append-only` hook rejects it — a database that
  already ran it would silently keep the old shape).
- Encode a table's rules as constraints where the database can check them (a `CHECK`, a
  partial unique index), not only in Python: then no code path, script or `psql` session can
  write a row that breaks them (e.g. `ck_ingestion_runs_state`, `ux_conversations_one_empty_per_user`).

## Adding a new implementation of an existing capability: satisfy the `Protocol`, don't branch on type

- A new variant (chunking strategy, archive store, tool, …) is a new class satisfying an
  existing (or new) `Protocol` in `rag.domain.ports`, wired in `container.py`.
- Never add an `if kind == ...` / `isinstance(...)` branch in the code that *consumes* the
  capability — that's the abstraction being bypassed rather than extended.

```python
class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Chunk]: ...
```

- Example: a new chunking strategy is a new `ChunkerPort` class, not a parameter threaded
  through the existing chunker.
- A new ingestion source (PDF, Confluence) is just a `load_*` function in `loaders.py` that
  returns `list[RawDocument]`; `IngestionService.ingest` takes documents, not a loader.

## Adding a new API route: thin router, `Annotated` deps, domain errors

- Module-level `router = APIRouter(prefix="/api/x", tags=["x"])` in `rag/api/routers/`, each
  endpoint a plain `@router.get`/`post` function. A gate every route shares goes on the router
  itself, next to its routes: `dependencies=[Depends(get_current_user)]` (or
  `get_current_admin`). A dependency only one route needs goes on that route.
- Take dependencies as `Annotated[T, Depends(...)]` aliases from `deps.py` (`ContainerDep`,
  `AuthenticatedUserDep`, `ConversationServiceDep`, …); never construct a service inline. `deps.py`
  holds only what several routers share (the container, services, auth); a dependency only one
  router uses is a private function in that router's module.
- A route reads as "call the service, shape the result" — business logic lives in the service.
- Return typed Pydantic models; use another response class (`EventSourceResponse`,
  `PlainTextResponse`) only when the body genuinely isn't JSON.
- In `app.py`, import the router object and add an `app.include_router(router)` line — no
  `dependencies=` there.
- App-level values reach routes through `app.state` (as `ContainerDep` does), not
  `dependency_overrides`, which is for tests.
- On failure, raise a `rag.domain.errors.AppError` subclass with a `status_code: ClassVar[int]`,
  never `fastapi.HTTPException` (ruff bans it). No change to `app.py`'s `register_error_handlers`
  is needed.
- Its frontend calls go in the matching `frontend/src/api/x.ts` (one module per router), through
  `authFetch` from `api/client.ts` — never a bare `fetch` or a token passed in by the caller
  (only `auth.ts`'s login/logout, which run before or without a token, use plain `fetch`; oxlint
  rejects `fetch` anywhere else). Components and pages never import `api/` (oxlint rejects that
  too): they get data and actions from a hook or context.
  Request/response types are the named types in `frontend/src/types/api.ts` (one per backend
  model, same name) — add the new model's line there, never a hand-written interface.

## Adding a user-owned resource: check ownership in the service, answer 404

- Look it up by id *and* check it against the caller in the service (example:
  `ConversationService.get_owned`), never in the router.
- Missing and someone-else's raise the same not-found error (404), so ids can't be probed.
- A streaming endpoint also gets a read-only gate on the route, defined next to it in its router
  module (`dependencies=[Depends(_require_owned_conversation)]`): a generator route's body only runs
  once the response has started, so a bad id raised there would be an error inside an
  already-200 stream instead of a clean 404.

## Adding a new SSE event

Each event of `POST /api/conversations/{id}/messages` is one `data:` line of JSON, told apart by
its `type`, and its shape is a Pydantic model, so it reaches the frontend through OpenAPI:
1. a dataclass in `rag/domain/events.py`, added to the `StreamEvent` union;
2. a Pydantic model with a `type: Literal[...]` in `rag/api/schema/conversations.py`, added to
   the `StreamEventResponse` root model's union, and its case in `_payload`;
3. its line in `frontend/src/types/api.ts` and its case in `createBubbleHandler`
   (`frontend/src/utils/chatStream.ts`) — whose `satisfies never` default fails to compile until
   the new event is handled.

The `frontend-api-types` pre-commit hook regenerates the types, and `frontend-typecheck` fails
if the frontend no longer matches them.

## Adding a new schema/DTO

- A new feature gets its own module in `rag/api/schema/`, mirroring `rag/api/routers/`, imported
  only by its own router.
- Keep request/response DTOs under `rag/api/`, never in `rag.domain` or a top-level
  `rag/schema/`.

## Adding a frontend type: shared ones in `types/`, private ones where they're used

- A type another file uses lives in `frontend/src/types/<feature>.ts` (`auth.ts`,
  `conversations.ts`, …), re-exported from `types/index.ts`, and is imported from `'../types'` —
  never from a hook or component file, nor from a single file inside `types/` (oxlint rejects
  both). Backend shapes go only in `types/api.ts` (see above).
- A type only one file uses (a component's props, a local helper signature) stays in that file.
- Before adding one, check `types/` for an equal type to reuse (e.g. `LoadStatus`).

## Adding a new closure-based dependency (a tool, a callback, any injected callable): close over it, don't reach for a global

- Write a `build_*(dependency) -> callable` closure, assembled wherever its owning service is
  built (example: `build_search_tool(knowledge_base)` in `tools.py`).
- Never a module-level global (e.g. a module-level `@tool` function), and never a client
  re-instantiated per call.

## Adding a new backend behind a `Settings`-driven choice: extend the discriminated union, don't branch downstream

- For a capability selected by configuration (today: `LLM`, `OBSERVABILITY`, `KB_STORAGE`), add a new Pydantic
  model to the discriminated union in `config.py`, keyed by its `BACKEND` literal and populated
  from nested env vars (`OBSERVABILITY__PUBLIC_KEY`).
- Add one `case` to the single `match` in the matching adapter (`llm_client.py`'s `build_llm`,
  `observability.py`'s `open_trace_config`, `archive_store.py`'s `open_archive_store`).
- Callers never branch on the active backend — they get a plain `BaseChatModel`, call
  `trace_config(name)`, or use an `ArchiveStorePort`.

## Adding a new secret

- **Local dev**: add it to `.env` (gitignored) and read it through `Settings`
  (`pydantic-settings`). Don't read `os.environ` directly outside `config.py`.
- **Prod**: add it to Azure Key Vault and reference it from App Service's Application Settings as
  a Key Vault reference — never as a plain env var with the value inline. See
  [reference.md#secrets-management](reference.md#secrets-management) for how the existing secrets
  are wired, and [infra.md](infra.md) for applying the Bicep template that provisions Key Vault
  access.
