# Run the local stack

## Description

Run Postgres, the backend and the frontend in Docker Compose.

## Steps

1. Fill `.env`. See [Local development](../../tutorials/local-development.md#2-configure-env).
2. Start the stack: `docker compose up --build`.
3. Open `http://localhost:3000`.
4. If the database is new, create a user. See [Manage users](manage-users.md).
5. If the database is new, load the knowledge base. See [Load the knowledge base](load-knowledge-base.md).
6. Stop the stack: `docker compose down`.

## Rules

* `backend` is not published to the host. Use the frontend URL for the UI and the API.
* `backend` starts only after `migrate` succeeds. If `backend` does not start, run `docker compose logs migrate`.
* `docker-compose.yml` overrides `DATABASE_URL` with the `postgres` host. Keep `localhost` in `.env`.
* `infra/docker/nginx.conf.template` reads the proxy target from `BACKEND_URL`, and each upload's body limit from the `UPLOADS__*` variables (`infra/docker/upload-limits.envsh`). The frontend container stops at start if one is missing; `docker-compose.yml` sets them once for both services (`x-upload-limits`).
