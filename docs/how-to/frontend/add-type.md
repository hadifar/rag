# Add a type

## Description

Decide where a TypeScript type lives.

## Steps

1. If the type is a backend shape, add one line to `frontend/src/shared/types/api.ts`.
2. If several features use the type, add it to `frontend/src/shared/types/` and re-export it from `index.ts`.
3. If several files of one feature use the type, add it to the feature's `types.ts`.
4. If one file uses the type, keep it in that file.
5. Check `frontend/src/shared/types/` for an equal type before you add one.

## Rules

* Import shared types from `@/shared/types`. Do not import a file inside it.
* Export a feature type to other features through the feature's `index.ts` with `export type`.
