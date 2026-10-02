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

- A new route joins the existing router for its area (`auth`, `conversation`, `ingestion`,
  `retrieval`, `setting`, `health`), even if it calls a service that router didn't use yet
  (e.g. a user's preferences are `/api/settings/preferences`, on `AgentService`). A router's
  file, and its schema module, is named after its area in the singular (`setting.py` serves
  `/api/settings`). A new router means a new area of the API: decide it on its own, never as a
  side effect of a feature. The one exception is `agent.py`: it shares `/api/conversations` to
  stream a turn, which `RagService` runs, not `ConversationService`.
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
- Its frontend calls go in the `api/` folder of the feature that owns them
  (`frontend/src/features/<feature>/api/x.ts`), through the typed `api` client from
  `shared/api/client.ts`, wrapped in `unwrap`:
  `unwrap(api.GET('/api/x/{x_id}', { params: { path: { x_id } }, signal }))`. The path, params,
  body and response are checked against the generated OpenAPI `paths`, so once the types are
  regenerated a renamed route or field fails `tsc`; `unwrap` returns the data or throws an
  `ApiError` carrying the status and the backend's `detail`. Every call goes through
  `authFetch` (token + one refresh-and-retry on a 401), never a bare `fetch` or a token passed
  in by the caller. Only three calls use the untyped `authFetch`/`apiUrl` (oxlint rejects them
  in any other `api/` file): the chat SSE stream, the multipart knowledge-base upload, and
  `features/auth/api/auth.ts`'s login/logout, which run before or without a token on plain
  `fetch`. Components and pages never import an `api/` (oxlint rejects that too): they get
  data and actions from a hook or context.
  Request/response types are the named types in `frontend/src/shared/types/api.ts` (one per
  backend model, same name) — add the new model's line there, never a hand-written interface.

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
1. a dataclass in `rag/domain/models/agent/stream.py`, added to the `StreamEvent` union and to
   the re-exports in `rag/domain/models/__init__.py`;
2. where it comes from in `rag/services/agent_service/streaming.py`: `parse_event` for the live
   stream and, if it should survive a reload, `replay` for history (rebuilt from the saved
   messages — anything not in them can't be replayed);
3. a Pydantic model with a `type: Literal[...]` in `rag/api/schema/agent.py`, added to
   the `StreamEventResponse` root model's union, and its case in `_payload`;
4. in the frontend (`frontend/src/features/chat/`), each step failing to compile until done:
   - its line in `frontend/src/shared/types/api.ts`;
   - its case in `applyEvent` (`model/transcript.ts`), whose `satisfies never` default rejects an
     unhandled event — a pure function, so test it in `tests/unit/utils/transcript.test.ts`;
   - if it makes a new kind of bubble: its variant in `Bubble` (`types.ts`), a component, and its
     entry in `bubbleViews` (`components/MessageList.tsx`), a map typed to need one per bubble type.

   History replays through the same `applyEvent`, so it needs nothing more.

The `frontend-api-types` pre-commit hook regenerates the types, and `frontend-typecheck` fails
if the frontend no longer matches them.

## Adding a new schema/DTO

- A new feature gets its own module in `rag/api/schema/`, mirroring `rag/api/routers/`, imported
  only by its own router.
- Keep request/response DTOs under `rag/api/`, never in `rag.domain` or a top-level
  `rag/schema/`.

## Adding a frontend feature: one folder, one public API

- A feature is a folder in `frontend/src/features/<name>/`, with only the layer folders it needs:
  `api/` (backend calls), `model/` (pure helpers), `hooks/` and `context/` (state + data access),
  `components/` (presentation), plus `types.ts` and `index.ts`. Keep the layer folders flat (no
  sub-folders): the lint's "don't climb out of a feature" rule relies on it.
- `index.ts` is the feature's public API: export only what another feature, a page or the app
  uses. Everything outside the feature imports `@/features/<name>`, never a file inside it
  (oxlint rejects both a deep `@/features/<name>/…` import and a relative `../../…` one).
- Inside the feature, import its own files by relative path; reach `shared/` through `@/shared/…`.
- A page in `src/pages/` composes features and holds no logic; a new route goes in
  `src/app/App.tsx`, its URL in `src/shared/routes.ts` (`routes.chat(id)`, `routePatterns.chat`),
  which every link, redirect and `useMatch` uses — never a URL spelled out elsewhere. A page that pulls in a heavy dependency is loaded with `lazy` (as `ChatPage`
  is).
- Something two features need that belongs to neither (a UI primitive, a generic hook) goes in
  `shared/`, which never imports a feature.

## Building frontend UI: shared primitives, colours by role

- Reach for `shared/ui` first: `Button` (`primary`/`secondary`/`danger`/`ghost`, or
  `size="icon"`), `IconButton` (a quiet icon-only action; its `label` is its accessible name),
  `Input`/`TextField`, `StatusLine` (loading, empty, saved, error — by `tone`), `Modal` /
  `ConfirmDeleteModal` for dialogs, and `BrandMark`/`APP_NAME`. Chat bubbles sit in the chat
  feature's `BubbleFrame`.
- A primitive's `className` is for layout only (margin, alignment, width, `flex-1`): its look
  comes from its props, so every button and field stays alike. A new look is a new variant in
  the primitive, not a class at the call site.
- Colours go by role — `primary-*`, `danger-*`, `success-*`, `warning-*`, defined once in
  `src/index.css`'s `@theme` — with Tailwind's `slate` for neutrals. Any other palette
  (`indigo-600`, `red-500`, …) fails `tests/unit/architecture/colors.test.ts`.
- Tailwind's preflight isn't loaded, so boxes are `content-box`: a full-width element with
  padding needs `box-border` (as `Input` has) to fit its container.

## Loading server data in the frontend: a query hook, never a fetch in an effect

- Read server data with `useQuery` (`useInfiniteQuery` for a paged list), change it with
  `useMutation`, inside a hook in the feature's `hooks/`. The hook returns what the UI needs
  (`status` via `loadStatus`, ready-to-show values, actions) — components and pages never import
  `@tanstack/react-query` (oxlint rejects it).
- Spell a feature's cache keys once, in its `api/queryKeys.ts` (`conversationKeys.list`), so a
  hook that patches or invalidates them can't drift from the one that reads them.
- After a mutation, patch the cache with `setQueryData` when the response says what changed
  (an added preference, a renamed chat); invalidate only when it doesn't. Another feature's
  cache is changed through a hook it exports (`useConversationCache`), never by its keys.
- Retries follow `shouldRetry` (`shared/api/queryClient.ts`): network errors and 5xx twice, never
  a 4xx. A query that needs otherwise (polling an ingestion run) sets its own `retry`.
- A delete treats a 404 as done (it's idempotent): `mutationFn: (id) => ignoreNotFound(deleteX(id))`.
- Tell the user what failed with `errorMessage(err, { 404: '…' }, fallback)` from
  `shared/api/errors.ts` — the feature words each message, the helper picks it by status — or
  `errorDetail(err)` where the backend's own reason is fit to show (an upload's rejection).
  Never `err instanceof ApiError && err.status === …` by hand.
- Navigation after a change (deleting the open chat) belongs to the hook that runs the user's
  action, not to the cache.

## Adding a frontend type: shared ones in `shared/types/`, feature ones in the feature

- A type several features use lives in `frontend/src/shared/types/` (e.g. `LoadStatus`),
  re-exported from its `index.ts` and imported from `'@/shared/types'` — never from a single file
  inside it (oxlint rejects that). Backend shapes go only in `shared/types/api.ts` (see above).
- A type used across one feature's files lives in that feature's `types.ts`; another feature gets
  it through the feature's `index.ts` (`export type …`).
- A type only one file uses (a component's props, a local helper signature) stays in that file.
- Before adding one, check `shared/types/` for an equal type to reuse.

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
