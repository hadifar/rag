# Contributing

## Setup

```
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
```

This runs `uv sync` and installs the git hooks for this clone. See
[docs/setup.md](docs/setup.md) for `.env`/`data/` setup and running the app (Python, CLI, or
Docker).

## Conventions & architecture

See [docs/conventions.md](docs/conventions.md) for coding style and the patterns to follow when
extending `rag/` (adding a service, a route, a tool, a backend, etc.).

## What's enforced automatically

Hooks run on every commit/push; run `pre-commit run --all-files` to check everything up front,
or `--no-verify` to deliberately skip a hook. See [docs/enforcement.md](docs/enforcement.md) for
the full list — linting, type checking, `import-linter` layering, Conventional Commits, gitflow
branch rules, and which test suite runs where.

## Test

```
uv run pytest                    # both suites
uv run pytest tests/unit         # fast, no external dependencies
uv run pytest tests/integration  # real Pinecone/OpenAI — needs PINECONE__API_KEY/LLM__API_KEY in .env
```

See [docs/enforcement.md#tests](docs/enforcement.md#tests) for what runs automatically vs. only
on manual dispatch.

## Frontend

See [frontend/README.md](frontend/README.md) for setup, dev server, and lint commands.
