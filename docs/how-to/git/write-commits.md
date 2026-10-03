# Write commits

## Description

Write a commit message. Commits follow [Conventional Commits](https://www.conventionalcommits.org/). Version bumps and `CHANGELOG.md` are generated from them.

## Steps

1. Write the message as `<type>(<scope>): <summary>`.
2. If a hook fixes files (`ruff`, `uv-lock`, `frontend-api-types`), stage the fixes and commit again.

## Rules

* Scope is optional. Scope names the area: `chat`, `agent`, `api`, `frontend`, `domain`, `config`, `cli`.
* Write the summary in the imperative mood, lowercase, without a final period.
* For a breaking change, add `!` after the scope.
* Do not start a message with `bump:`. The `bump-version` workflow reserves `bump:`.
* Do not commit `.env` or `infra/azure/main.parameters.local.json`.

## Version effect

| Commit | Bump while version is `0.x` |
|---|---|
| `fix` | patch |
| `feat` | minor |
| breaking (`!`) | minor |
| other types | none |

## Example

```text
feat(chat): stream the model's reasoning summary
fix: raise the graph recursion limit to 75
refactor(frontend): move server state to TanStack Query
```
