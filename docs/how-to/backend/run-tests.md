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
* Retrieval eval (real knowledge base, local only):
    1. Load the knowledge base. See [Load the knowledge base](../infra/load-knowledge-base.md).
    2. Add questions to `tests/eval/retrieval_questions.jsonl`. Format: see `tests/eval/test_retrieval.py`.
    3. Run: `uv run pytest tests/eval`. The run ends with recall@k and MRR.
* All checks: see [Run validation](../run-validation.md).

## Rules

* Put tests without network or database access in `tests/unit/`. Use `tests/unit/fakes.py`.
* Put tests against Postgres or the LLM provider in `tests/integration/`.
* Integration tests fail, not skip, when a required setting is missing.
* Put retrieval-quality checks against the real knowledge base in `tests/eval/`. They run only when `tests/eval` is named on the command line, so no CI job runs them.
