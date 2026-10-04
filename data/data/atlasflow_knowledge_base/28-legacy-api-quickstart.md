# Legacy API Quickstart

_Last reviewed: 2025-05_

> This quickstart was originally written for early Growth onboarding and may not reflect the latest product defaults or terminology.

If you want to start integrating quickly, the basic idea is simple:

1. Ask a team administrator to create an API credential.
2. Send requests to the AtlasFlow REST API.
3. Handle paging if your workspace has a lot of records.
4. Back off when you hit rate limits.

## Who should create the key?

For a shared integration, ask a **team administrator** to create the credential and store it securely.

For personal scripting, use your own developer credential.

## Example request pattern

Use bearer authentication when calling the API.

Example:

`Authorization: Bearer <token>`

## Growth default rate limit

For most Growth workspaces, the default rate limit is **120 requests per minute**.

If your integration sends bursts of traffic, add retries and backoff rather than assuming every request will succeed.

## Tips

- Keep the credential server-side.
- Cache list responses where possible.
- Do not poll more often than needed.
- Use retry handling when the API pushes back.

## Terminology note

Some newer admin screens may use different role names than this guide. If you cannot find “team administrator” in the current UI, use the closest current administrative role with integration privileges.
