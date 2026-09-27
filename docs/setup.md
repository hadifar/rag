# Setup & Running

## Setup
```bash
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
```
Then fill in `.env` (see .example.env) `LLM__API_KEY`, `PINECONE__API_KEY`, etc.

**You need a `data/` folder in the repo root with your own `.md` files** — it's gitignored, so a
fresh clone doesn't come with one. `KNOWLEDGE_BASE_DIR` (default `data`) points `rag ingest` at it,
and `Dockerfile.backend` does `COPY data/ data/`, so it must exist (even if just with a placeholder
`.md`) before `docker compose up --build`, or the image build fails.

If running via Docker (below), also create the Postgres init password Docker Compose expects,
gitignored and never read by the app itself:
```bash
mkdir -p .secrets
openssl rand -base64 24 | tr -d '=+/' | tr -d '\n' > .secrets/postgres_password.txt
```
Then make sure `.env`'s `CHECKPOINTER__DATABASE_URL` uses that same password (the app connects with it
directly; `.secrets/postgres_password.txt` is only used to initialize the `postgres` container).

Auth (login) uses the same Postgres instance via `AUTH__DATABASE_URL` — set it to the same value as
`CHECKPOINTER__DATABASE_URL` above, and set `AUTH__JWT_SECRET` to a random value (e.g. `openssl rand
-hex 32`). Before serving for the first time — and after pulling changes that add a migration — apply the
migrations (`users`, `conversations`) and create a user (there's no public signup — accounts are
created out-of-band):
```bash
uv run alembic upgrade head
uv run rag create-user you@example.com
```

## Running

### Python (uv)
```bash
uv run python -m rag serve
```
If `.env` has `CHECKPOINTER__BACKEND=postgres`, a Postgres instance must be reachable at
`CHECKPOINTER__DATABASE_URL` — either `docker compose up -d postgres` (published on
`localhost:5432`; adjust its host to `localhost` when running the app outside Docker) or set
`CHECKPOINTER__BACKEND=memory` for a dependency-free local run.

### CLI
```bash
uv run rag ingest   # embeds data/*.md and upserts into Pinecone — run once before serving
uv run rag serve
```

### Docker
```bash
docker compose up --build
```
Starts `postgres` (checkpointer + auth/users storage, published on `localhost:5432`), `backend`,
and the frontend (nginx) on `http://localhost:3000`; the `backend` container isn't published to
the host, only reachable inside the compose network. nginx proxies `/api/*` to it, so use the
frontend URL for both the UI and the API.

Requires `.secrets/postgres_password.txt` to exist first — see [Setup](#setup) above.

Once the stack is up, apply the `users` table migration and create a login (one-time, or after a
fresh `pgdata` volume) — the backend serves fine without this, but nothing can log in until it's
done:
```bash
docker compose exec backend alembic upgrade head
docker compose exec backend rag create-user you@example.com
```

```bash
docker compose down   # stop and remove the containers
```



### Frontend
```bash
cd frontend
npm install
npm run dev   # UI at http://localhost:5173, proxies API calls to :8000
```
See [frontend/README.md](../frontend/README.md).

## CI vs. production config

`.github/workflows/integration-tests.yml` hardcodes `LLM__BACKEND=openai`, `AUTH__DATABASE_URL`
(pointing at a throwaway Postgres service container) and a dummy `AUTH__JWT_SECRET`. That's only
safe because the database lives for a single job. In production, never hardcode these: take them
from GitHub `secrets` (credentials, such as `AUTH__DATABASE_URL`, which contains the DB password,
and `AUTH__JWT_SECRET`) or `vars` (non-sensitive choices such as `LLM__BACKEND`), the same way the
workflow already reads `OPENAI_API_KEY` and `PINECONE_*`.
