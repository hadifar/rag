# Add a page

## Description

Add a route and its page. Use when the app needs a new URL.

## Steps

1. Add the URL to `routes` in `frontend/src/shared/routes.ts`.
2. If the route has params, add the pattern to `routePatterns`.
3. Create `frontend/src/pages/<Name>Page.tsx`. Compose features only.
4. Add the route to `frontend/src/app/App.tsx`.
5. If the page imports a heavy dependency, load it with `lazy`. Example: `ChatPage`.
6. Add an integration test in `frontend/tests/integration/<Name>Page.test.tsx`.
7. Validate the change. See [Run validation](../run-validation.md).

## Rules

* A page holds no logic.
* Build every link and redirect from `routes`. Do not write a URL string elsewhere.
* Only `frontend/src/pages/ChatPage.tsx` and `frontend/src/pages/SharedChatPage.tsx` import `@/features/chat`. Both are loaded with `lazy`.
