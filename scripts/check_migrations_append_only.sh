#!/usr/bin/env bash
# Fails if a committed migration was modified, renamed or deleted: a database that already
# ran it would never see the change (the schema silently drifts). Add a new migration instead.
#
#   no argument  checks the staged changes (the pre-commit hook)
#   <base-ref>   checks everything since <base-ref> (CI, against the pull request's base)
#
# A deliberate exception, e.g. squashing migrations before 1.0:
#   SKIP=migrations-append-only git commit ...
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ $# -gt 0 ]]; then
  changed=$(git diff --name-only --diff-filter=MDR "$1"...HEAD -- migrations/versions/)
else
  changed=$(git diff --cached --name-only --diff-filter=MDR -- migrations/versions/)
fi

if [[ -n "$changed" ]]; then
  echo "Migrations are append-only, but these existing ones changed:" >&2
  echo "$changed" | sed 's/^/  /' >&2
  echo "Add a new migration instead: uv run alembic revision -m '...'" >&2
  exit 1
fi
