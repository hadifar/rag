# Enforcement — What's Automatically Checked

Mechanisms that catch a problem automatically (pre-commit hook or CI), not conventions that
just rely on review discipline.

## Commit & branch hygiene
- Conventional Commits: `commitizen` (commit-msg stage) plus `cz check` on every pull request
  in CI (`pre-commit.yml`'s `commitizen` job)
- Gitflow, via `precommit-gitguard`: `no-direct-commit` (master/dev only accept merges),
  `no-direct-push`, `branch-name` (must follow `feat/fix/refactor/docs/chore/release/hotfix`),
  `stale-branch`

## Python code quality
- `ruff --fix` + `ruff-format` on every commit
- `pyright` type checking at the `pre-push` stage
- `import-linter` (`lint-imports`) enforces the layered architecture in `rag/`
  (`pyproject.toml`'s `[tool.importlinter]`):
  - `rag.domain` may not import `rag.services`, `rag.adapters`, or `rag.api` ("domain is pure")
  - `rag.services` may not import `rag.adapters` directly
  - `rag.api` may not import `rag.adapters` directly (except `container.py`, explicitly ignored)
  - an explicit layering contract: `rag.api` → `rag.services` → `rag.domain`
- `uv-lock` keeps `uv.lock` in sync with `pyproject.toml`, auto-fixing locally

## Backend/frontend schema sync
- The `frontend-api-types` pre-commit hook regenerates
  `frontend/src/types/api.generated.ts` from the backend's OpenAPI schema whenever
  `rag/api/schema.py` or `rag/api/routers/*.py` change (`scripts/generate_frontend_types.sh`) —
  auto-fixes locally like `uv-lock`, and re-runs in CI so a stale generated file fails the
  `pre-commit` job
- `frontend/src/types/index.ts` re-exports the whole schema map as
  `Schemas = components['schemas']` rather than hand-picked aliases, so there's no per-type
  step that could fall out of sync — a new backend schema is just `Schemas['NewType']`

## Tests
- `pytest tests/unit` runs on every commit (pre-commit hook) and again in CI
  (`pre-commit.yml`'s `test` job)
- `pytest tests/integration` only runs on manual `workflow_dispatch`
  (`integration-tests.yml`) — **not** a merge gate

## General file hygiene
`trailing-whitespace`, `end-of-file-fixer`, `check-yaml`, `check-added-large-files`
(max 1000kb), `check-merge-conflict`, `debug-statements` — standard `pre-commit-hooks`

## What CI actually gates on PR / push to master
`pre-commit.yml` runs three jobs: the full pre-commit suite, `pytest tests/unit`, and (PR only)
the Conventional Commits check across the PR's commit range.
