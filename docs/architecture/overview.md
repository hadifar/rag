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

Each turn (`conversation_turns`) is kept two ways.

* `answer` is what the user saw: the streamed events.
* `agent_messages` is the agent's memory of the turn: its question, tool calls, tool results and answers, rejected drafts included. It is NULL for a turn the agent forgot (blocked, failed, or cut short). Each turn, the chat service hands the agent the memory of the earlier turns.
* A user has at most one untitled conversation.

A user can attach files (`.md`, `.png`, `.jpg`) to a message.

* `POST /api/conversations/{id}/attachments` stores a file in `conversation_attachments` (as `bytea`). The backend checks the file's content, not the type the client sends.
* The chat request lists the files by `attachment_ids`. `conversation_turn_attachments` links each turn to the files it was sent with, in order. A retry sends the same files again.
* The agent's memory stores only attachment ids. Every model call reads the files again, so a later turn still sees an earlier image.
* `rag prune-attachments` deletes files that were uploaded but never sent.

Each conversation has a model (`gpt-6-luna`, `gpt-6-astra` or `gpt-6-sol`) and an effort (`low`, `medium` or `high`), on `conversations`. The user picks them in the composer (`PATCH /api/conversations/{id}`); a new chat applies its picks when its first message creates it.

* The model is the one the provider is called with (for Azure, the deployment name). Only the agent's answers use it; titles and the guards run on `LLM__MODEL`.
* The effort is sent as the model's reasoning effort, only when `LLM__REASONING_EFFORT` is set (reasoning models).

A user can save skills: SKILL.md files with YAML frontmatter (`name`, `description`) and markdown instructions, uploaded alone or in a `.zip`/`.skill` archive with reference files (text only).

* `POST /api/skills` parses the file and stores it in `user_skills`, and an archive's reference files in `user_skill_files`. A skill with the same name as an existing one replaces it. `GET /api/skills` lists them, and `DELETE /api/skills/{id}` deletes one.
* A user's skills apply to all of their conversations. The agent sees each skill's name and description on every turn, and loads a skill's instructions (`load_skill`) when a question fits its description. It reads a reference file (`read_skill_file`) when the instructions call for it.
* A message that starts with `/<name>` invokes that skill: the turn starts with it loaded. The composer suggests the user's skills while a `/` command is typed.
* Skills change how the agent answers, not where facts come from. The groundedness guard ignores `load_skill` and `read_skill_file` results. Skills are untrusted input: see [Limitations](../limitations.md#security).

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
