# Setup & Running

## Setup
```bash
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
```
Then fill in `.env` (see .example.env).

The knowledge base is the `.md` files in `data/`. `KNOWLEDGE_BASE_DIR` (default `data`) points
`rag ingest` at that folder. The backend image doesn't contain `data/`: ingestion only writes
chunks into Postgres, so it runs from the host (or with `data/` mounted, see [Docker](#docker)) and
the serving container reads them from the database. To use your own knowledge base instead, put
your `.md` files in `data/`.

The default `DATABASE_URL` in `.example.env` already matches the local `postgres` compose service
(user/password `rag`, bound to `127.0.0.1:5432` only) — no change needed for local dev. That one
database holds everything: users, conversations, their messages and the knowledge-base chunks.

For login, set `AUTH__JWT_SECRET` to a random value (e.g. `openssl rand -hex 32`). Before serving for the first time — and after pulling changes that add a migration — apply the
migrations (`users`, `conversations`, `chunks`) and create a user (there's no public signup — accounts are
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
A Postgres instance (with pgvector) must be reachable at `DATABASE_URL` — e.g.
`docker compose up -d postgres` (published on `localhost:5432`). There's no in-memory mode.

`.env`'s `DATABASE_URL` points at `localhost`, which is right for anything run on your machine
(`uv run …`, `alembic`). The `backend` container overrides it with the `postgres` host in
`docker-compose.yml` (`environment:` beats `env_file:`), so the same `.env` works for both.

### CLI
```bash
uv run rag ingest   # embeds data/*.md and upserts the chunks into Postgres — run once before serving
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

Once the stack is up, apply the `users` table migration and create a login (one-time, or after a
fresh `pgdata` volume) — the backend serves fine without this, but nothing can log in until it's
done:
```bash
docker compose exec backend alembic upgrade head
docker compose exec backend rag create-user you@example.com
```

Then ingest the knowledge base (one-time, or after changing `data/`, or after a fresh `pgdata`
volume). The image has no `data/`, so mount it (see [Setup](#setup)) into a one-off `backend`
container; without this, chat answers have no sources:
```bash
docker compose run --rm -v "$PWD/data:/app/data:ro" backend ingest
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

`.github/workflows/integration-tests.yml` hardcodes `LLM__BACKEND=openai`, `DATABASE_URL`
(pointing at a throwaway Postgres service container) and a dummy `AUTH__JWT_SECRET`. That's only
safe because the database lives for a single job. In production, never hardcode these: take them
from GitHub `secrets` (credentials, such as `DATABASE_URL`, which contains the DB password,
and `AUTH__JWT_SECRET`) or `vars` (non-sensitive choices such as `LLM__BACKEND`), the same way the
workflow already reads `OPENAI_API_KEY`.
