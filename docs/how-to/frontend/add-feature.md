# Add a feature

## Description

Add a frontend feature folder. Use for a new product area with its own data or UI.

## Steps

1. Read [Frontend architecture](../../architecture/frontend.md).
2. Create `frontend/src/features/<name>/`.
3. Add only the layer folders the feature needs: `api/`, `model/`, `hooks/`, `context/`, `components/`.
4. Add `types.ts` for types shared inside the feature.
5. Add `index.ts`. Export only what pages, the app or other features use.
6. Copy the shape of the closest feature. Example: `frontend/src/features/preferences/`.
7. Add tests. See [Run frontend tests](run-tests.md).
8. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Keep layer folders flat. Do not add sub-folders.
* Outside the feature, import `@/features/<name>` only.
* Inside the feature, import files by relative path. Import `shared/` as `@/shared/...`.
* Put code that two features need and neither owns in `frontend/src/shared/`.
* `shared/` never imports a feature, a page or `app/`.
