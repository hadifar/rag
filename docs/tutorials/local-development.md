# Local development

Run the backend with `uv` and the frontend with Vite. Finish with a signed-in chat that cites the knowledge base.

## Prerequisites

* `uv` ([install](https://docs.astral.sh/uv/getting-started/installation/))
* Docker with Docker Compose
* Node.js 22 and `npm`
* An OpenAI or Azure OpenAI API key

## 1. Install

```bash
git clone https://github.com/hadifar/rag.git && cd rag
bash scripts/setup.sh
```

`scripts/setup.sh` runs `uv sync`, installs the git hooks and copies `.example.env` to `.env`.

## 2. Configure `.env`

1. Fill in the `LLM__*` values.
2. Set `OBSERVABILITY__BACKEND=logging`. Use `langfuse` only with Langfuse keys.
3. Keep `DATABASE_URL` as it is. The value matches the `postgres` compose service.
4. Keep `AUTH__JWT_SECRET` as it is for local development.

## 3. Start Postgres and migrate

```bash
docker compose up -d postgres
uv run alembic upgrade head
```

## 4. Create a user

```bash
uv run rag create-user you@example.com --admin
```

The command prompts for a password. The app has no public signup.

## 5. Load the knowledge base

```bash
uv run rag ingest
```

`rag ingest` indexes `data/data.zip`. Re-run it after you change the knowledge base. Only new and changed files are embedded.

## 6. Start the backend

```bash
uv run rag serve
```

The API listens on `http://localhost:8000`. The OpenAPI UI is at `http://localhost:8000/docs`.

## 7. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`. Sign in with the user from step 4. Ask a question about the knowledge base.

## 8. Run the checks

Follow [Run validation](../how-to/run-validation.md).

## Next

* Run everything in containers: [Run the local stack](../how-to/infra/run-local-stack.md).
* Learn the system: [Architecture overview](../architecture/overview.md).
* Make a change: [How-to guides](../README.md#how-to-guides).
