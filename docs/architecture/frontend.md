# Frontend

The frontend in `frontend/` is organized by feature first, then by layer.

Diagram: [Frontend layers](../diagrams/architecture.md#frontend-layers).

## Layers inside a feature

* `api/`: calls the backend. Imports nothing else from the feature.
* `model/`: pure functions. No network, no framework state, no UI.
* `hooks/`, `context/`: state and data access with TanStack Query.
* `components/`: presentation only. Never imports `api/` or `@tanstack/react-query`.
* `index.ts`: the feature's public API. Other code imports `@/features/<name>` only.

oxlint (`frontend/.oxlintrc.json`) enforces every rule above.

## State

* Server data lives in the TanStack Query cache.
* `AuthProvider` is the only app-wide context. It holds the session.
* Logout clears the cache.

## Backend types

* `npm run generate:types` writes `src/shared/types/api.generated.ts` from the backend OpenAPI schema.
* `src/shared/types/api.ts` exports one named type per backend model.
* A renamed backend field fails the frontend type check. Diagram: [Schema sync](../diagrams/schema-sync.md).
