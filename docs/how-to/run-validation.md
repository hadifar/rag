# Run validation

## Description

Validate a change before you commit or open a pull request. Every how-to guide ends here.

## Steps

1. Add or update tests for behavior changes.
2. Run all checks from the repo root: `uv run pre-commit run --all-files`.
3. If you changed `frontend/`, run the frontend tests from `frontend/`: `npx vitest run`.
4. Update `docs/` when behavior changes.

What each check enforces: [Enforcement](../architecture/enforcement.md).
