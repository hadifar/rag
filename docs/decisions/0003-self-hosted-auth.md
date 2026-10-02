# 0003. Self-hosted JWT auth

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

The app needs sign-in. Clerk, Auth0 and Entra ID were considered.

## Decision

Issue JWTs in the backend. Store users in Postgres with `argon2` hashes. Keep the access token in memory and the refresh token in an httpOnly cookie. Create accounts with `rag create-user`.

## Consequences

* No external identity dependency.
* No signup, password reset or email verification.
* No token rotation or revocation.
