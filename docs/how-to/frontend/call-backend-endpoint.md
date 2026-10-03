# Call a backend endpoint

## Description

Call a backend route from the frontend. Use after you add or change a route.

## Steps

1. Run `npm run generate:types`. The `frontend-api-types` hook also runs the script on commit.
2. Add one line per new backend model to `frontend/src/shared/types/api.ts`.
3. Add the call to `frontend/src/features/<name>/api/<name>.ts`.
4. Call the typed `api` client from `frontend/src/shared/api/client.ts`, wrapped in `unwrap`.
5. Call the function from a hook. See [Load server data](load-server-data.md).
6. Validate the change. See [Run validation](../run-validation.md).

## Rules

* Do not edit `frontend/src/shared/types/api.generated.ts`.
* Do not write an interface for a backend shape by hand.
* Do not call `fetch`. oxlint rejects a bare `fetch`.
* Three calls use the untyped `authFetch`: the chat SSE stream, the multipart upload, and login/logout in `features/auth/api/auth.ts`. Do not add another.

## Example

`frontend/src/features/knowledge-base/api/ingestions.ts`:

```ts
return unwrap(api.GET('/api/ingestions/{run_id}', { params: { path: { run_id: id } } }));
```
