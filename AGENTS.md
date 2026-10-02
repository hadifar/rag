# Agent Instructions

## Before you change code

1. Open the how-to guide for the task from the [docs index](docs/README.md). Follow its steps.
2. If no guide covers the task, read the matching page in [docs/architecture/](docs/architecture/).
3. Copy the shape of the closest existing example.


## Ask the user first

- Before you add a route to `_PUBLIC_ROUTES` in `tests/unit/test_app.py`.
- Before you add a new router (a new API area).
- Before you change `pyproject.toml`, `frontend/package.json` , `infra/azure/main.bicep`, `.github/workflows/`, or `.gitignore`

## Never do

- Edit `frontend/src/shared/types/api.generated.ts` by hand.
- Edit a committed migration in `migrations/versions/`.
- Run `az` or `gh` commands that change live Azure or GitHub state.

## After you change code

1. Follow [Run validation](docs/how-to/run-validation.md).
2. Write a short report: what changed, which checks ran and their results, and anything left undone.
