# Docs

- [architecture.md](architecture.md) — diagrams: system overview, backend layering, the
  LangGraph generation graph, frontend structure
- [auth.md](auth.md) — why the frontend and backend share one origin, and what that buys auth
- [services.md](services.md) — per-service detail that doesn't fit a diagram (guard middleware,
  …)
- [reference.md](reference.md) — what exists today: tech stack, layout, services, conversation
  state, authentication, streaming, observability, secrets, API surface
- [conventions.md](conventions.md) — patterns to follow when adding to the codebase: a
  service/adapter, a repository, an ingestion source, an API route, a user-owned resource, an SSE
  event, a schema, a tool, an LLM/observability backend, a secret
- [enforcement.md](enforcement.md) — what's automatically checked (pre-commit hooks, CI gates)
- [limitation.md](limitation.md) — known gaps, not yet addressed
- [infra.md](infra.md) — Docker + Azure infra, how to deploy
- [setup.md](setup.md) — local dev setup
