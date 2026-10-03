# Modify a workflow

## Description

Change a GitHub Actions workflow in `.github/workflows/`.

## Steps

1. Run `uv run pre-commit run check-yaml --all-files`.
2. Update the CI section of [Enforcement](../../architecture/enforcement.md#ci) when a trigger or job changes.
3. Commit with type `ci`: `ci: <summary>`.
4. If the workflow is manual, run it from the Actions tab on the branch.

## Rules

* Read credentials from `secrets`. Read non-sensitive choices from `vars`.
* Hardcode a credential only for a throwaway service inside one job. Example: the Postgres service in `integration-tests.yml`.
* Keep `fetch-depth: 0` in `pre-commit.yml`. `no-direct-commit` needs merge parents.
* Do not trigger `bump-version.yml` from a `bump:` commit.
