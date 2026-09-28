#!/usr/bin/env bash

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

if ! command -v uv >/dev/null 2>&1; then
    echo "error: uv is not installed — https://docs.astral.sh/uv/getting-started/installation/" >&2
    exit 1
fi

echo "==> Installing dependencies (uv sync)"
uv sync

echo "==> Installing git hooks"
uv run pre-commit install

if [ ! -f .env ]; then
    echo "==> Creating .env from .example.env"
    cp .example.env .env
    echo "    Fill in the LLM__* and OBSERVABILITY__* values; DATABASE_URL and AUTH__JWT_SECRET work as-is for local dev."
else
    echo "==> .env already exists, leaving it as-is"
fi

echo
echo "Setup complete. Next:"
echo "  docker compose up -d postgres      # local Postgres (pgvector) on localhost:5432"
echo "  uv run alembic upgrade head        # apply migrations"
echo "  uv run rag create-user you@example.com   # there's no public signup"
echo "  uv run rag ingest                  # build the vector index from data/"
echo "  uv run rag serve                   # start the API on :8000 (UI: cd frontend && npm run dev)"
