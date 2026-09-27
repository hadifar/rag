# Setup & Running

## Setup
```bash
git clone https://github.com/hadifar/rag.git
cd rag
bash scripts/setup.sh
```
Then fill in `.env` (see .example.env) `LLM__API_KEY`, the database URLs, etc. The Postgres
server needs the `pgvector` extension — the Docker Compose `postgres` service
(`pgvector/pgvector:pg17`) has it; `alembic upgrade head` enables it.

**The knowledge base ships zipped** — the repo holds only `data/data.zip`, not the `.md` files
themselves. `scripts/setup.sh` extracts it into `data/` (skipped if `data/*.md` already exists); to
do it by hand, from the repo root:
```bash
unzip data/data.zip   # extracts the .md files into data/
```
`KNOWLEDGE_BASE_DIR` (default `data`) points `rag ingest` at that folder, and `Dockerfile.backend`
does `COPY data/ data/`, so unzip before `rag ingest` or `docker compose up --build`, or nothing
gets ingested. To use your own knowledge base instead, put your `.md` files in `data/`.

If running via Docker (below), also create the Postgres init password Docker Compose expects,
gitignored and never read by the app itself:
```bash
mkdir -p .secrets
openssl rand -base64 24 | tr -d '=+/' | tr -d '\n' > .secrets/postgres_password.txt
```
Then make sure `.env`'s `DATABASE_URL` uses that same password (the app connects with it
directly; `.secrets/postgres_password.txt` is only used to initialize the `postgres` container).
That one database holds everything: users, conversations, their messages and the
knowledge-base chunks.

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

The host in `DATABASE_URL` depends on where the app runs. The name `postgres` only resolves inside
the compose network, so outside Docker it fails with `failed to resolve host 'postgres'`:

| App runs | `DATABASE_URL` host |
|---|---|
| on your machine (`uv run …`, `rag serve`, `rag create-user`, `alembic`) | `localhost` |
| in the `backend` container (`docker compose up`) | `postgres` |

The `backend` container reads the same `.env` (`env_file: .env`), so keep `.env` on one of the two and
override the other on the command line, e.g.
`DATABASE_URL=postgresql://rag:<password>@localhost:5432/rag uv run rag serve`.

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

`.github/workflows/integration-tests.yml` hardcodes `LLM__BACKEND=openai`, `DATABASE_URL`
(pointing at a throwaway Postgres service container) and a dummy `AUTH__JWT_SECRET`. That's only
safe because the database lives for a single job. In production, never hardcode these: take them
from GitHub `secrets` (credentials, such as `DATABASE_URL`, which contains the DB password,
and `AUTH__JWT_SECRET`) or `vars` (non-sensitive choices such as `LLM__BACKEND`), the same way the
workflow already reads `OPENAI_API_KEY`.
