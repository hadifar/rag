# System overview

A RAG chat app: a React frontend, a FastAPI backend with a LangChain agent, and one Postgres database with `pgvector`.

Diagram: [System overview](../diagrams/architecture.md#system-overview).

## Request path

* The browser talks to one origin.
* nginx (containers) or the Vite dev server (local) proxies `/api/*` to the backend.
* The refresh-token cookie works because the browser sees one origin.

## Data and state

One Postgres database (`DATABASE_URL`) holds everything.

* The `public` schema belongs to Alembic.
* The `langgraph` schema is left over from the LangGraph checkpointer. Nothing uses it.

Each turn (`conversation_turns`) is kept two ways.

* `answer` is what the user saw: the streamed events.
* `agent_messages` is the agent's memory of the turn: its question, tool calls, tool results and answers, rejected drafts included. It is NULL for a turn the agent forgot (blocked, failed, or cut short). Each turn, the chat service hands the agent the memory of the earlier turns.
* A user has at most one untitled conversation.

The knowledge base is a zip or directory of `.md` files (`KNOWLEDGE_BASE_SOURCE`, default `data/data.zip`).

* The file basename is the document id.
* Ingestion syncs the index to the source in one transaction: it embeds new and changed files and deletes missing files.
* `POST /api/ingestions` stores the zip, then ingests it in the background. One run at a time.

## Authentication

Self-hosted JWT auth. Diagram: [Auth flow](../diagrams/auth-flow.md).

* No public signup. `rag create-user` creates users. Only admins upload the knowledge base.
* The access token (15 min) travels as `Authorization: Bearer` and lives in frontend memory only.
* The refresh token (7 days) is an httpOnly cookie on `/api/auth`.
* `authFetch` refreshes once on a 401, then retries.
* `get_current_user` guards every route except `auth` and `health`. `get_current_admin` guards `ingestions`.

## Read next

* [Backend](backend.md)
* [Frontend](frontend.md)
* [Limitations](../limitations.md)
