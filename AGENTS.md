# Agent Instructions

A production ready RAG application.

## Repository map

- `rag/`: backend: `api/`, `services/`, `domain/`, `adapters/`, `repository/`, `config/`
- `frontend/`: React app, one folder per feature in `src/features/`
- `migrations/`: Alembic schema migrations
- `tests/`: backend tests: `unit/` , `integration/`
- `infra/`: Dockerfiles, nginx, Azure Bicep.
- `.github/workflows/`: CI.
- `scripts/`: setup and code-generation scripts.
- `data/`: sample knowledge base (zip format).
- `docs/`: documentation: `how-to/`, `architecture`
- `CONTRIBUTING.md`, `README.md`:  human guidance

## Before code change

1. Open the how-to guide for the task from the [docs index](docs/README.md) and read the relevant section(s).
2. If no guide covers the task, read the matching page in [docs/architecture/](docs/architecture/).
3. Inspect existing implementations and tests to verify.


## Ask the user first

- Before you add a new router (a new API area).
- Before you change `pyproject.toml`, `frontend/package.json` , `infra/azure/main.bicep`, `.github/workflows/`, or `.gitignore`

## Never do

- Run `az` or `gh` commands that change live Azure or GitHub state.

## After code change

1. Follow [Run validation](docs/how-to/run-validation.md).
2. Write a short report: what changed, which checks ran and their results, and anything left undone.
