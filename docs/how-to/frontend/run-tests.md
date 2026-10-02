# Run frontend tests

## Description

Run the frontend tests. Run every command from `frontend/`.

## Steps

* Unit and integration tests: `npx vitest run`.
* Type check and lint: see [Run validation](../run-validation.md).

## E2E

1. From the repo root, start Postgres: `docker compose up -d postgres`.
2. From the repo root, migrate: `uv run alembic upgrade head`.
3. Set `DATABASE_URL` in `.env` to a `localhost` host.
4. From `frontend/`, run `E2E_EMAIL=<email> E2E_PASSWORD=<password> npm run test:e2e`.

`npm run test:e2e` installs Chromium when missing.

## Rules

* Test pure helpers in `frontend/tests/unit/`.
* Test whole pages in `frontend/tests/integration/` with MSW.
