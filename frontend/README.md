# Frontend

React + TypeScript chat UI for the RAG backend, built with Vite, Tailwind CSS v4 and React Router.

## Install

```bash
npm install
```

## Run

```bash
npm run dev      # dev server with HMR
npm run build    # type-check and production build
npm run preview  # serve the production build
npm run lint     # oxlint
npm run test     # see test section bellow
```

The dev server proxies `/api` to
the backend at `http://localhost:8000` (see [vite.config.ts](vite.config.ts)), so start the
backend first. To sign in or chat, run the
backend first (Postgres, migrations, a user, ingest): see [docs/setup.md](../docs/setup.md).

## Test

## Unit & Integration
Unit (Pure helpers and single components) and integration (whole page with its real hooks, context and API client) tests both run in Vitest (jsdom) and need no backend:

```bash
npm test          # both, watch mode
npx vitest run    # both, once
npx vitest run tests/unit   # only unit
npx vitest run tests/integration # only integeration
```

### E2E
E2E test with the real stack in Chromium

```bash
# must be in repo root
docker compose up -d postgres
uv run alembic upgrade head

# frontend/ (installs Chromium first if missing)
E2E_EMAIL=admin@admin.com E2E_PASSWORD=admin npm run test:e2e
```

The backend also needs a filled `../.env`, with `localhost` as the `DATABASE_URL` host (see
[docs/setup.md](../docs/setup.md#python-uv)). `npm run test:e2e` then does the rest, in order:
