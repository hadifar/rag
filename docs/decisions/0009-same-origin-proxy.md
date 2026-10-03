# 0009. Same-origin `/api` proxy

Status: Accepted
Date: 2026-10-02 (recorded from earlier design)

## Context

The refresh token is a cookie. Cross-origin cookies need CORS and `SameSite=None`.

## Decision

The browser talks to one origin. nginx (containers) and Vite (local) proxy `/api/*` to the backend. On Azure, the backend has no public access.

## Consequences

* No CORS configuration.
* `SameSite=Lax` cookies work.
* The frontend is the only path to the backend.
