# Enforcement

The project prefers a failing build over a review comment. This page lists what is checked and where.

## Pre-commit hooks

`uv run pre-commit run --all-files` runs every hook in `.pre-commit-config.yaml`. CI runs the same hooks.

* `ruff`: lint and format. Bans `fastapi.HTTPException`, `os.environ`, `os.getenv`, `os.path`, `print()`. Bans blind `except Exception`, unreferenced `create_task()`, and mutable class attributes. Max complexity 5, nesting 3, 20 statements, 8 locals, 5 arguments, 5 returns, 12 public methods per class.
* `pyright`: type check. Strict everywhere except `rag/services/`.
* `import-linter`: the backend layer rules in [Backend](backend.md#layers).
* `pytest tests/unit`: unit tests. `tests/unit/test_app.py` fails when a route outside `_PUBLIC_ROUTES` has no auth dependency.
* `migrations-append-only`: rejects a change to a committed migration.
* `frontend-api-types`: regenerates `frontend/src/shared/types/api.generated.ts` from the backend schema.
* `frontend-typecheck`: `tsc` against the regenerated types. A renamed backend field fails here.
* `frontend-oxlintrc`: regenerates `frontend/.oxlintrc.json` from `scripts/generate_oxlintrc.mjs`.
* `frontend-lint`: `oxlint`, the frontend layer rules in [Frontend](frontend.md#layers-inside-a-feature).
* `commitizen`: Conventional Commits, on the commit message.
* `precommit-gitguard`: `master` and `dev` accept merges only; branch names start with `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`, `release/` or `hotfix/`.

Hooks that fix files: `ruff`, `uv-lock`, `frontend-api-types`, `frontend-oxlintrc`. Stage the fixes and run the checks again.

## Tests outside the hooks

* `tests/unit/architecture/colors.test.ts` (frontend): only role colors and `slate`.
* Frontend tests (`npx vitest run`): local only. No CI job runs them.
* Integration tests (`tests/integration`): manual workflow only. The workflow also checks every migration with `downgrade base` and `upgrade head`.

## CI

Merge gates (`pre-commit.yml`, on each pull request and each push to `master`):

* `pre-commit` job: every hook above, `pytest tests/unit` included.
* `commitizen` job: commit messages and append-only migrations across the pull request.

Not merge gates:

* `bump-version.yml` (push to `master`): bumps the version, updates `CHANGELOG.md`, tags.
* `integration-tests.yml` (manual): integration tests and the migration round trip.
* `build-push.yml` (manual): builds and pushes images to ACR.
* No workflow runs the frontend tests or deploys.
