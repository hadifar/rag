# Run backend tests

## Description

Run the Python test suites.

## Steps

* Unit tests (no external services): `uv run pytest tests/unit`.
* Integration tests:
    1. Fill `.env` with a real `LLM__*` key.
    2. Start Postgres: `docker compose up -d postgres`.
    3. Migrate: `uv run alembic upgrade head`.
    4. Run: `uv run pytest tests/integration`.
* All checks: see [Run validation](../run-validation.md).

## Rules

* Put tests without network or database access in `tests/unit/`. Use `tests/unit/fakes.py`.
* Put tests against Postgres or the LLM provider in `tests/integration/`.
* Integration tests fail, not skip, when a required setting is missing.
