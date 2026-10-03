# Load server data

## Description

Read or change server data in a hook. Use for every backend read or write from the UI.

## Steps

1. Add the cache keys to `frontend/src/features/<name>/api/queryKeys.ts`.
2. Create a hook in `frontend/src/features/<name>/hooks/`.
3. Read with `useQuery`. Read a paged list with `useInfiniteQuery`.
4. Write with `useMutation`.
5. After a mutation, patch the cache with `setQueryData` when the response says what changed.
6. If the response does not say what changed, invalidate the key.
7. Return what the UI needs: `status` (via `loadStatus`), display values, actions.
8. Add a test in `frontend/tests/integration/` with MSW (`frontend/tests/server.ts`).

## Rules

* Do not fetch in a `useEffect`.
* Spell each cache key once, in `api/queryKeys.ts`.
* Change another feature's cache only through a hook that feature exports. Example: `useConversationCache`.
* Retries follow `shouldRetry` in `frontend/src/shared/api/queryClient.ts`. Set `retry` on the query only to override `shouldRetry`.
* Treat a 404 on delete as done: `mutationFn: (id) => ignoreNotFound(deleteX(id))`.
* Word error messages with `errorMessage(err, { 404: '...' }, fallback)`. Do not compare `err.status` by hand.
* Navigate after a change in the hook that runs the action.
