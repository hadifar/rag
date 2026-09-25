# Contributing

## Setup

```
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
```

This runs `uv sync` and installs the git hooks (`pre-commit`, `commit-msg`, `pre-push`, `post-checkout` stages) for this clone. Hooks run automatically; run `pre-commit run --all-files` to check everything up front.

- **pre-commit** — `ruff` (lint + format) and `import-linter` (enforces the `domain`/`services`/`adapters`/`api`/`ui` layering in `pyproject.toml`)
- **commit-msg** — [Conventional Commits](https://www.conventionalcommits.org/) via `commitizen` (e.g. `fix: handle missing session UUID`, `feat: add search highlighting`)
- **pre-push** — `pyright` (type checking); also blocks direct (non-merge) commits to `master`/`dev`, and requires new branches to follow the gitflow prefix convention: `feat/`, `fix/`, `refactor/`, `docs/`, `chore/`, `release/`, `hotfix/`
- **post-checkout** — warns (non-blocking) if `master`/`dev` is behind its upstream after a checkout

Deliberate override for any of these: `--no-verify`.

## Commit messages

Commits must follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g. `fix: handle missing session UUID`, `feat: add search highlighting`), enforced by the `commitizen` hook.


## Test

```
uv run pytest
```

Runs both suites:
- `tests/unit` — fast, no external dependencies (FastAPI wired up with stub services via `create_app(container=...)`).
- `tests/integration` — against real Pinecone/OpenAI, requires `PINECONE__API_KEY`/`LLM__API_KEY` in `.env` (see `tests/integration/conftest.py`); skips with a clear reason if they're missing.

Run just one: `uv run pytest tests/unit` or `uv run pytest tests/integration`.

## Frontend

See [frontend/README.md](frontend/README.md) for setup, dev server, and lint commands.
