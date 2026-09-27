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
- Routers and services never import `rag.adapters` or `rag.repository` — they take a
  `rag.domain.ports` `Protocol` in their constructor, and `container.py` supplies the concrete
  instance. `import-linter` enforces this ([enforcement.md](enforcement.md#python-code-quality)).

## Adding a new repository: SQL behind a domain port

- Put it in `rag/repository/`, implementing a `Protocol` from `rag.domain.ports` (example:
  `UserRepositoryPort` → `rag/repository/user_repository.py`), and wire it in `container.py`.
- `adapters/` is for wrapped third-party SDK clients
  instead.
- Schema changes go in a new Alembic revision under `migrations/versions/`.

## Adding a new implementation of an existing capability: satisfy the `Protocol`, don't branch on type

- A new variant (ingestion source, chunking strategy, tool, …) is a new class satisfying an
  existing (or new) `Protocol` in `rag.domain.ports`, wired in `container.py`.
- Never add an `if kind == ...` / `isinstance(...)` branch in the code that *consumes* the
  capability — that's the abstraction being bypassed rather than extended.

```python
class DocumentLoaderPort(Protocol):
    def load(self) -> Iterable[RawDocument]: ...


class ChunkerPort(Protocol):
    def chunk(self, document: RawDocument) -> list[Document]: ...
```

- Example: a new source (PDF, Confluence) is a new `DocumentLoaderPort` class; `IngestionService`,
  the chunkers and the repository stay untouched. A new chunking strategy is a new `ChunkerPort`
  class, not a parameter threaded through existing chunkers.

## Adding a new API route: thin router, `Annotated` deps, domain errors

- Module-level `router = APIRouter(prefix="/api/x", tags=["x"])` in `rag/api/routers/`, each
  endpoint a plain `@router.get`/`post` function.
- Take dependencies as `Annotated[T, Depends(...)]` aliases from `deps.py` (`ContainerDep`,
  `SettingsDep`, `CurrentUserDep`, …); never construct a service inline.
- A route reads as "call the service, shape the result" — business logic lives in the service.
- Return typed Pydantic models; use a `Response` subclass (`StreamingResponse`,
  `PlainTextResponse`) only when the body genuinely isn't JSON.
- In `app.py`, import the router object and `app.include_router(router, dependencies=...)`. The
  prefix stays on the router; `dependencies=` is only for a gate every route shares (e.g.
  `[Depends(get_current_user)]`). A dependency only one route needs goes on that route.
- App-level values reach routes through `app.state` (as `SettingsDep`/`ContainerDep` do), not
  `dependency_overrides`, which is for tests.
- On failure, raise a `rag.domain.errors.RagError` subclass with a `status_code: ClassVar[int]`,
  never `fastapi.HTTPException`. No change to `app.py` or `error_handlers.py` is needed.
- Its frontend calls go in the matching `frontend/src/api/x.ts` (one module per router), through
  `authFetch` from `api/client.ts` — never a bare `fetch` or a token passed in by the caller
  (only `auth.ts`'s login/logout, which run before or without a token, use plain `fetch`).
  Request/response types come from the generated `Schemas`, not hand-written interfaces.

## Adding a user-owned resource: check ownership in the service, answer 404

- Look it up by id *and* check it against the caller in the service (example:
  `ConversationService._get_owned`), never in the router.
- Missing and someone-else's raise the same not-found error (404), so ids can't be probed.
- If a streaming endpoint uses it, resolve it before the `StreamingResponse` starts (`start_turn`),
  so a bad id is a clean 404 instead of an error inside an already-200 stream.

## Adding a new SSE event

The `/api/chat/stream` wire format is hand-kept in four places; change all four together:
1. a dataclass in `rag/domain/events.py`, added to the `StreamEvent` union;
2. its encoder in `_ENCODERS` in `rag/api/routers/chat.py` — `data` must be single-line JSON
   (`json.dumps`/`model_dump_json`), never raw text, or a `\n\n` ends the event early;
3. its name in `STREAM_EVENT_TYPES` in `frontend/src/api/chat.ts` and its member of
   `ChatStreamEvent` in `frontend/src/types/chat.ts` (the event's JSON fields are spread into it);
4. `test_chat_stream_contract_matches_frontend_parsing` in `tests/unit/test_app.py`, the only
   check that catches the two sides drifting apart.

## Adding a new schema/DTO

- A new feature gets its own module in `rag/api/schema/`, mirroring `rag/api/routers/`, imported
  only by its own router.
- Keep request/response DTOs under `rag/api/`, never in `rag.domain` or a top-level
  `rag/schema/`.

## Adding a new closure-based dependency (a tool, a callback, any injected callable): close over it, don't reach for a global

- Write a `build_*(dependency) -> callable` closure, assembled wherever its owning service is
  built (example: `build_search_tool(ranking_service)` in `tools.py`).
- Never a module-level global (e.g. a module-level `@tool` function), and never a client
  re-instantiated per call.

## Adding a new backend behind a `Settings`-driven choice: extend the discriminated union, don't branch downstream

- For a capability selected by configuration (today: `LLM`, `OBSERVABILITY`), add a new Pydantic
  model to the discriminated union in `config.py`, keyed by its `BACKEND` literal and populated
  from nested env vars (`OBSERVABILITY__PUBLIC_KEY`).
- Add one `case` to the single `match` in the matching adapter (`llm_client.py`'s `build_llm`,
  `observability.py`'s `open_trace_config`).
- Callers never branch on the active backend — they get a plain `BaseChatModel` or call
  `trace_config(name)`.

## Adding a new secret

- **Local dev**: add it to `.env` (gitignored) and read it through `Settings`
  (`pydantic-settings`). Don't read `os.environ` directly outside `config.py`.
- **Prod**: add it to Azure Key Vault and reference it from App Service's Application Settings as
  a Key Vault reference — never as a plain env var with the value inline. See
  [reference.md#secrets-management](reference.md#secrets-management) for how the existing secrets
  are wired, and [infra.md](infra.md) for applying the Bicep template that provisions Key Vault
  access.
