---
name: git-commit
description: Split work into single-purpose commits and write their messages in this repo's format. Use when creating git commits, writing commit messages, or when the user says "git-commit".
---

# Git Commit

Turn the working tree into small commits that each make one logical change, with a conventional message.

## Format

```
<type>(<scope>): <description>

<optional body>
```

- **type**: a commitizen type: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, …
- **scope**: the area affected: `backend`, `frontend`, `ci`, `infra`, `docs`, …
- **description**: completes "If applied, this commit will ___". Imperative, lowercase, under 72 chars.
- **body**: optional. Say why, not how. Leave a blank line after the subject, and start each paragraph with a capital letter.

Example: `fix(backend): handle empty retrieval results`

## One logical change per commit

If a change can be split into a sequence of commits, split it. Never mix unrelated changes in one commit.

- **Refactoring**: always separate from functional changes.
- **Bug fixes**: one bug is one commit, even across files.
- **Features**: one feature is one commit, or one per logical sub-part.
- **Dependencies**: group related ones. Split unrelated ones.

Many files can still be one change. When in doubt, split: squashing later is easier than untangling. Use `git add -p` to stage parts of a file.

## Never

- Commit to `dev` or `master`. Branch first.
- Use `--force`, `reset --hard`, or other destructive commands unless asked.
- Skip hooks (`--no-verify`) unless asked.
