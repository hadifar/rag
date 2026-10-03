# Manage users

## Description

Create users and change admin rights. The app has no public signup.

## Steps

* Create an admin (uv): `uv run rag create-user you@example.com --admin`.
* Create an admin (Compose): `docker compose exec backend rag create-user you@example.com --admin`.
* Grant admin: `uv run rag set-admin <email>`.
* Revoke admin: `uv run rag set-admin <email> --revoke`.
* On Azure, run `rag create-user` where `DATABASE_URL` points at the production database.

## Rules

* Only admins can upload the knowledge base.
* Rotating `AUTH__JWT_SECRET` signs every user out.
