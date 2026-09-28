# Contributing

## Setup

See [docs/setup.md](docs/setup.md) for setup and running the app (uv, docker compose or azure).

## Conventions & architecture

See [docs/conventions.md](docs/conventions.md) for coding style and the patterns to follow when
extending `rag/`.

## What's enforced automatically

Hooks run on every commit/push; See [docs/enforcement.md](docs/enforcement.md) for
the full list — linting, type checking, `import-linter` layering, Conventional Commits, gitflow
branch rules, and which test suite runs where.

## Test

```
uv run pytest                    # both suites
uv run pytest tests/unit         # fast, no external dependencies
uv run pytest tests/integration  # real OpenAI + Postgres (pgvector) — needs a filled .env and `alembic upgrade head`
```

See [docs/enforcement.md#tests](docs/enforcement.md#tests) for what runs automatically vs. only
on manual dispatch.

## Frontend

See [frontend/README.md](frontend/README.md) for setup, dev server, lint and test commands (Vitest unit/integration, Playwright e2e).
