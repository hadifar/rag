# Add a migration

## Description

Change the database schema with Alembic. Use for every table, column, index or constraint change.

## Steps

1. Start Postgres: `docker compose up -d postgres`.
2. Create the revision: `uv run alembic revision -m "<summary>"`.
3. Rename the file to the next number: `migrations/versions/00NN_<summary>.py`.
4. Set `revision` to the next number (`"0011"`) and `down_revision` to the previous number (`"0010"`).
5. Write `upgrade()` and `downgrade()`.
6. Apply it: `uv run alembic upgrade head`.
7. Check the round trip: `uv run alembic downgrade -1 && uv run alembic upgrade head`.
8. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Never edit a committed migration. The `migrations-append-only` hook rejects the change.
* Write `downgrade()` for every migration. CI runs `downgrade base`.
* Put Alembic tables in `public`.
* Encode table rules as constraints: `CHECK`, partial unique index. Example: `ck_ingestion_runs_state`, `ux_conversations_one_empty_per_user`.
* Do not add ORM models. `migrations/` is the only schema source.
