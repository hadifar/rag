# Auth

The browser only ever sees one origin (e.g., `http://local:3000`) — it never knows the
backend's hostname. nginx proxies `/api/*` to `BACKEND_URL`
(`infra/docker/nginx.conf.template`), and Vite's dev server proxies the same path locally
(`vite.config.ts`). This matters for auth too: the refresh token is a same-site cookie, which
only works cleanly because the browser only ever talks to one origin — there's no cross-origin
cookie problem to solve.
