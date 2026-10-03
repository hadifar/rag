# Frontend Review Guide (React + TanStack Query)

> **This repo:** Vite SPA, React 19, TanStack Query v5. Server data lives only in the TanStack Query cache, read and written in feature hooks. Components are presenters.

Code reaching review already passes oxlint and `tsc`. Flag only an `oxlint-disable` added without a stated reason.

## Severity

Most performance findings are **P2**. Raise one to **P1** only on a hot path (the chat stream re-renders on every token, the conversation list, first load), and say what the user sees. Ignore micro-optimizations outside loops and hot paths.

## Components and state

- **Logic in `components/`**: parsing, date math, sorting, or mapping API shapes. Move it to the feature's `model/`.
- **Server data copied into `useState`** from a hook's result. It goes stale. Read it from the query, or derive it.
- **Duplicated or derivable state** stored twice. The copies drift apart. Use `useReducer` for several related transitions.
- **Event logic in an effect** (`useEffect` that watches state to run analytics or a request). Move it into the event handler (`rerender-move-effect-to-event`).
- **Effects without cleanup** that add a listener, start a timer, or open a stream. Cleanup means `removeEventListener`, `clearInterval`, or `AbortController`.
- **Index keys** on lists that reorder, insert, or delete (messages, conversations). State and focus attach to the wrong row.
- **`{count && <X/>}`** renders `0` when `count` is 0. Use a ternary (`rendering-conditional-render`).
- **`arr.sort()` on props or query data** mutates shared data. Use `toSorted()` (`js-tosorted-immutable`).
- **A new app-wide context**. `AuthProvider` is the only one. For prop drilling, prefer composition (`children`).

## Memoization (proportionate)

- `useMemo`/`useCallback` on cheap values, or callbacks not passed to a memoized child or a dependency array, are noise (`rerender-simple-expression-in-memo`).
- `React.memo` that receives a new object, array, or function each render memoizes nothing. That includes non-primitive default props like `items = []` (`rerender-memo-with-default-value`). Inline values passed to non-memoized children are fine.
- `setX(prev => …)` keeps callbacks stable and avoids stale reads (`rerender-functional-setstate`).
- `useState(() => expensive())` for costly initial values (`rerender-lazy-state-init`).

## TanStack Query v5

- **`queryKey` covers every input the `queryFn` reads.** Otherwise a changed input never refetches and different inputs share one cache entry.
- **Share key and fn** through `queryOptions(...)` when both a hook and a prefetch or `getQueryData` use them.
- **`staleTime`** defaults to 0, so every mount and focus refetches. It should fit the data. Retries go through `shouldRetry`. A per-query `retry` needs a reason.
- **Mutations invalidate** every query showing the changed data. A missing invalidation leaves the UI stale. A keyless `invalidateQueries()` refetches everything.
- **Optimistic updates**: manual `onMutate` needs `cancelQueries` plus rollback in `onError`. The simpler v5 form renders the pending `variables`. Never be optimistic about deletes or anything irreversible.
- **Status**: `isPending` means no data yet. `isLoading` is `isPending && isFetching`, so it is false for a disabled query. `if (isLoading) …; data!` crashes when the query is disabled.
- **`useSuspenseQuery`** has no `enabled` (put the condition in the parent), no `error` field (errors throw), and needs a `Suspense` plus an error boundary above it.
- **Dependent-query waterfalls**: a child's query starts only after the parent's resolves, though it doesn't need that data. Fetch both in the hook or prefetch them (`async-parallel`).
- **Use `select`** so a component re-renders only when its slice changes (`rerender-derived-state`).
- **User data must not outlive logout.** The query cache is cleared on logout. Check any new store (`localStorage`, module variables) is too.

## React 19

- **Writes go through `useMutation`.** Don't suggest replacing it with `useActionState`.
- **`use(promise)`**: a promise created in the same render is recreated every render and suspends forever. It must come from a cache or a stable parent.
- **`useFormStatus`** only works in a child rendered inside the `<form>`.
- **`Suspense` or `React.lazy`** added without an error boundary: one thrown error blanks the whole tree. Use separate boundaries for independent regions.
- **`<Activity>`** hides UI and keeps its state, instead of unmounting it (`rendering-activity`).

## Performance

- **Waterfalls**: sequential `await`s that don't depend on each other should use `Promise.all` (`async-parallel`). Move an `await` into the branch that uses it (`async-defer-await`). Check cheap sync conditions first (`async-cheap-condition-before-await`).
- **Bundle**: load heavy, rarely used UI with `React.lazy` (`bundle-dynamic-imports`) and preload it on hover or focus (`bundle-preload`). Keep dynamic import paths statically analyzable; ``import(`./${x}`)`` bundles every match (`bundle-analyzable-paths`). Load analytics after first render (`bundle-defer-third-party`). Flag new large dependencies; they also need `package.json` approval.
- **Re-renders** (matter most in `features/chat`): subscribe only to the state you render (`rerender-defer-reads`). Mark non-urgent updates with `startTransition` (`rerender-transitions`). Use `useDeferredValue` for expensive renders behind input (`rerender-use-deferred-value`). Keep transient values like scroll position in a ref (`rerender-use-ref-transient-values`). Split hooks that mix independent dependencies (`rerender-split-combined-hooks`).
- **Rendering**: use `content-visibility: auto` for long transcripts or lists (`rendering-content-visibility`). Hoist static JSX (`rendering-hoist-jsx`). Animate a wrapper `div`, not the SVG (`rendering-animate-svg-wrapper`).
- **Browser**: one shared global listener rather than one per component (`client-event-listeners`). `{ passive: true }` for scroll, touch, and wheel (`client-passive-event-listeners`). Version the shape of anything in `localStorage` (`client-localstorage-schema`).
- **Hot loops only**: `Map`/`Set` lookups instead of `find`/`includes` (`js-index-maps`, `js-set-map-lookups`). Hoist `RegExp`s (`js-hoist-regexp`). Find min/max with a loop, not by sorting (`js-min-max-loop`). Combine chained passes (`js-combine-iterations`).
- **Not applicable here** (Next.js or SSR only): `server-*`, `async-api-routes`, `rendering-hydration-*`.

## Security

- `dangerouslySetInnerHTML` with API, document, or model content is XSS: **P0**.
- `react-markdown` is safe by default. Adding `rehype-raw` or allowing raw HTML on model output or retrieved documents removes that.
- Links from model output or documents: block `javascript:` URLs. Use `rel="noopener noreferrer"` with `target="_blank"`.
- Tokens in `localStorage`/`sessionStorage`: check against `AuthProvider`'s design before flagging.

## Tests

- `@testing-library/react`, `screen.*ByRole`, `userEvent` over `fireEvent`.
- Network mocked with `msw`, not by mocking hooks. Assert what the user sees.
- New `model/` functions have plain unit tests. No CI job runs frontend tests, so note whether they were run.
