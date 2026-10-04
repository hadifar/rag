# Load the knowledge base

## Description

Index the knowledge base into Postgres. Run after a new database or a knowledge-base change.

## Steps

* From the UI: sign in as an admin. Upload a `.zip` of `.md` files under **Settings → Knowledge base**.
* With uv: `uv run rag ingest`.
* With uv, from another source: `uv run rag ingest --source <path>`.
* With Compose: `docker compose run --rm -v "$PWD/data:/app/data:ro" backend ingest`.
* Rebuild from the newest upload: `rag ingest --latest`.
* Re-embed everything: `rag ingest --force`.

## Rules

* The backend image contains no `data/`. Mount `data/` or upload through the UI.
* Use `--force` after you change the embedding model or the chunker.
* Start each `.md` file with a `# title` and a one-paragraph description under it. Search scores the title, the description and the other headings as the document's summary.
* Do not run `rag ingest` while an upload is running.
