# Enforcement — What's Automatically Checked

Mechanisms that catch a problem automatically (pre-commit hook or CI), not conventions that
just rely on review discipline.

Generally, we prefer make the wrong thing fail to build instead of relying on review or discipline.

## Commit & branch hygiene
- Conventional Commits: `commitizen` (commit-msg stage) plus `cz check` on every pull request
  in CI (`pre-commit.yml`'s `commitizen` job)
- Gitflow, via `precommit-gitguard`: `no-direct-commit` (master/dev only accept merges),
  `no-direct-push`, `branch-name` (must follow `feat/fix/refactor/docs/chore/release/hotfix`),
  `stale-branch`

## Python code quality
- `ruff --fix` + `ruff-format` on every commit. Beyond the defaults, it turns convention rules
  into errors (`pyproject.toml`'s `[tool.ruff.lint]`):
  - banned APIs (`TID251`): `fastapi.HTTPException` (raise a `RagError` subclass instead) and
    `os.environ` / `os.getenv` (configuration comes through `rag.config.Settings`); tests may
    read the environment
  - `FAST`: FastAPI dependencies declared with `Annotated`, no redundant `response_model`
  - `T20`: no `print()` (the CLI uses `typer.echo`); scripts that write to stdout are exempt
  - `C901` with a max complexity of 5, plus `B`, `SIM`, `RET`, `UP`, `ERA`, `PTH`, `ASYNC`, …
- `pyright` on every commit (pre-commit stage, so CI runs it too): **strict** for
  `rag/domain`, `rag/api`, `rag/repository`, `rag/adapters` and the top-level modules, basic for
  `rag/services`, where LangChain's partly untyped API leaks in
- `import-linter` (`lint-imports`) enforces the architecture in `rag/`
  (`pyproject.toml`'s `[tool.importlinter]`):
  - `rag.domain` may not import `rag.services`, `rag.adapters`, `rag.repository`, or `rag.api`
    ("domain is pure")
  - `rag.services` may not import `rag.adapters`, `rag.repository` or the entrypoints
  - only the composition root (`container.py`) constructs adapters or repositories
  - `rag.api` may not import the entrypoints (`app.py`, `cli.py`)
  - within `rag.api`, only `deps.py` reaches `rag.services` and the container; routers get
    services through its `Annotated` aliases
  - routers are independent of each other
  - services are independent of each other, except `generation_service` using
    `retrieval_service` for its search tool (the one allowed exception)
  - an explicit layering contract: `rag.api` → `rag.services` → `rag.domain`
- `uv-lock` keeps `uv.lock` in sync with `pyproject.toml`, auto-fixing locally

## Backend/frontend schema sync
- The `frontend-api-types` pre-commit hook regenerates
  `frontend/src/types/api.generated.ts` from the backend's OpenAPI schema whenever
  `rag/api/schema/*.py` or `rag/api/routers/*.py` change (`scripts/generate_frontend_types.sh`) —
  auto-fixes locally like `uv-lock`, and re-runs in CI so a stale generated file fails the
  `pre-commit` job
- `frontend/src/types/api.ts` is the one place backend shapes enter the frontend: one named
  type per model in `rag/api/schema/`, same name, grouped by module (`ConversationResponse`,
  `ToolEvent`, …); the generated `components` map isn't exported, so nothing else can reach
  around it. A backend model renamed or removed breaks its line there (`tsc`, via the
  `frontend-typecheck` pre-commit hook); a new one needs its line added before the frontend can
  use it — the one manual step, and it can't drift silently
- `frontend-typecheck` (pre-commit, and CI's `pre-commit` job) runs `tsc -b` over the frontend,
  so code that no longer matches the regenerated types fails instead of breaking at runtime;
  `createBubbleHandler`'s `satisfies never` default makes a new stream event type one of those
  failures (the stream union is a named root model, `StreamEventResponse`, so it's generated too)

## Tests
- `pytest tests/unit` runs on every commit (pre-commit hook) and again in CI
  (`pre-commit.yml`'s `test` job)
- Architecture tests among them check what no linter can:
  `test_every_route_requires_a_signed_in_user_unless_public` walks every route (router-level
  dependencies included) and fails if one outside a short public allowlist (login, refresh,
  logout, health) doesn't depend on `get_current_user`, so a new route or router can't ship
  unauthenticated; the allowlist can't go stale either, since a public route that became
  protected fails it too
- `pytest tests/integration` only runs on manual `workflow_dispatch`
  (`integration-tests.yml`) — **not** a merge gate. That job starts a throwaway Postgres, runs
  `alembic upgrade head` (so it also exercises the migrations), and fails — rather than skips —
  when a required setting is missing, so it can't pass green with zero tests run

## General file hygiene
`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`
(max 1000kb), `check-merge-conflict`, `debug-statements` — standard `pre-commit-hooks`

## What CI actually gates on PR / push to master
`pre-commit.yml` runs three jobs: the full pre-commit suite (ruff, pyright, import-linter, unit
tests, the frontend type sync and type check, …), `pytest tests/unit`, and (PR only) the
Conventional Commits check across the PR's commit range.
