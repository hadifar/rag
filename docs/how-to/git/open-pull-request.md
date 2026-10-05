# Open a pull request

## Description

Merge a branch through a pull request. Use for every change.

## Steps

1. Validate the change. See [Run validation](../run-validation.md).
2. Open the pull request against `dev`.
3. If the branch is a `hotfix/` branch, open the pull request against `master`.
4. Wait for the `pre-commit` and `commitizen` jobs to pass.
5. Merge with a merge commit.

## Rules

* List the tests you ran.
* Do not add a route to `_PUBLIC_ROUTES` in `tests/unit/test_app.py` without reviewer approval.
