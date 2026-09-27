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
    echo "    Fill in your LLM provider key and the database URLs before running 'serve' or 'ingest'."
else
    echo "==> .env already exists, leaving it as-is"
fi

echo
echo "Setup complete. Next:"
echo "  uv run alembic upgrade head        # create the users table"
echo "  uv run rag create-user you@example.com   # there's no public signup"
echo "  uv run rag ingest                  # build the vector index from data/"
echo "  uv run rag serve                    # start the API + UI"
