---
name: scan-repo
description: Repo-wide design audit. Returns a ranked list of what to delete, simplify, or replace with built-ins or established libraries. Use when the user says "scan repo", "scan codebase", or "audit repo". Reports only. It never edits code. Not for bugs or security.
---

# Scan Repo

Audit the whole tree, not a diff. Find over-engineering, needless complexity, and structure that will get in the way as the code grows. Keep good architecture: SOLID, clean layers.

Reports only. It never edits code. Not for bugs or security (use `pr-review`).

## 1. Map before judging

- Read `docs/architecture/` and `docs/decisions/`. A documented decision is intentional. Report it only as `challenges docs/decisions/<file>`, with the reason.
- Read the enforcement config: ruff and import-linter in `pyproject.toml`, `.pre-commit-config.yaml`, and the frontend lint config. Do not report what a tool already enforces.
- Scan one area at a time: backend layers, then frontend features, then infra and scripts.
- Skip generated or frozen files: `api.generated.ts`, `openapi.json`, `migrations/`, lockfiles, `data/`.

## 2. Tag each finding with what replaces the code

| Tag | Replacement | Must name |
|---|---|---|
| `delete` | Nothing: dead code, unused options, dead flags or config, speculative features | The grep that found no callers |
| `inline` | The caller: a factory with one product, a wrapper that only delegates, a module that only re-exports | The call site it collapses into |
| `reuse` | A helper or pattern that already exists in this repo | Its path |
| `builtin` | The stdlib or platform (Python, browser, React, FastAPI, Postgres, nginx) | The function or feature |
| `lib` | A canonical, well-established package. Use it only when no built-in fits. Needs user approval | The package and what it replaces |
| `shrink` | The same logic in fewer lines | The shorter form |
| `restructure` | A different boundary: a layer leak, a god module, a misplaced responsibility, a circular dependency | Where the code should live |
| `enforce` | A build-time rule that stops the problem from coming back | The tool and the rule or contract |

Also look for code smells, anti-patterns, and outdated or deprecated APIs. Use the tag of the fix.

## 3. Keep what earns its place

- An interface on a layer boundary (a port) stays, even with one adapter. So does any interface with a test fake.
- An adapter that wraps a third-party SDK stays. It is the anti-corruption layer.
- A file per concept and a folder per feature stay. Flag them only when they are empty indirection.

## 4. Verify before emitting

- `delete` / `inline`: grep the whole tree for the symbol, including tests, fixtures, strings, and dynamic references (`getattr`, registries, DI wiring, router includes, lazy imports, config keys).
- `builtin` / `lib`: confirm the replacement works on the project's Python and Node versions.
- If a finding cannot be verified, drop it.

## 5. Rank by what waiting costs

- **HIGH**: compounds. Each new feature copies it or has to work around it.
- **MEDIUM**: contained. It costs time now but stays in one place.
- **LOW**: cosmetic. Fewer lines, no change to the design.

Within a level, put the best payoff for the least effort first. Report at most 20 findings.

## 6. Report the findings

```
- [HIGH] [restructure] rag/services/chat.py:40 — builds SQL inline → move to rag/repository/
- [MEDIUM] [builtin] rag/domain/text.py:12 — hand-rolled slugify loop → re.sub + str.casefold
- [LOW] [shrink] frontend/src/features/chat/useChat.ts:88 — 9-line reduce → Object.groupBy
```

Format: `- [<SEVERITY>] [<tag>] <path:line> — <problem> → <fix>`.

If nothing survives verification: `- Already clean <3!`
