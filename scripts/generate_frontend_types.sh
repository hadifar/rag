#!/usr/bin/env bash
# Regenerates frontend/src/types/api.generated.ts from the backend's OpenAPI
# schema, keeping request/response types in sync across the language boundary.
set -euo pipefail
cd "$(dirname "$0")/.."

uv run python scripts/export_openapi.py > openapi.json
(cd frontend && npx --no-install openapi-typescript ../openapi.json -o src/types/api.generated.ts)
