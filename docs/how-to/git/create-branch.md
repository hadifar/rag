# Create a branch

## Description

Create a branch for a change. Use before every change. `master` and `dev` accept merges only.

## Steps

1. Branch from `dev`.
2. If the change fixes production, branch from `master`.
3. Name the branch `<type>/<short-kebab-description>`.

## Rules

* Use one of these types: `feat`, `fix`, `refactor`, `docs`, `chore`, `release`, `hotfix`.
* Use one branch per change.
* The `branch-name` hook rejects other names.

## Example

```bash
git checkout -b feat/add-feedback-capability
```
