# Frontend

React + TypeScript chat UI for the RAG backend. Built with Vite, Tailwind CSS v4, React Router and TanStack Query.

## Quick start

Start the backend first. See [Local development](../docs/tutorials/local-development.md).

```bash
npm install
npm run dev
```

Open `http://localhost:5173`. The dev server proxies `/api` to `http://localhost:8000`.

## Commands

| Command | Does |
|---|---|
| `npm run dev` | Dev server with HMR |
| `npm run build` | Type check and production build |
| `npm run preview` | Serve the production build |
| `npm run generate:types` | Regenerate backend API types |
| `npm run test:e2e` | E2E tests against the real stack |

## Docs

* [Frontend architecture](../docs/architecture/frontend.md)
* [Frontend how-to guides](../docs/how-to/frontend/)
* [Run validation](../docs/how-to/run-validation.md)
* [Run frontend tests](../docs/how-to/frontend/run-tests.md)
* [All documentation](../docs/README.md)
