# API Rate Limits

_Last updated: 2026-01-15_

This document defines the current default AtlasFlow API rate-limit behavior.

## General model

AtlasFlow applies rate limits to protect platform stability and to ensure fair use across tenants.

Unless otherwise stated by contract, rate limits are evaluated at the workspace level across relevant API traffic.

## Default request limits by plan

- **Starter:** 60 requests per minute
- **Growth:** 180 requests per minute
- **Enterprise:** 600 requests per minute by default

Enterprise customers may have higher limits where explicitly agreed by contract.

## Burst behavior

Short bursts above the steady-state minute limit may still trigger rate limiting depending on traffic shape and endpoint mix. Clients should not assume that sending the entire minute allocation in one instant will always succeed.

## 429 behavior

When rate limiting is enforced, AtlasFlow returns:

- HTTP `429 Too Many Requests`
- a `Retry-After` header indicating when the client should retry

Clients should back off rather than retry immediately in a tight loop.

## Recommendations

AtlasFlow recommends that API clients:

- respect the `Retry-After` header
- implement exponential backoff for repeated 429 responses
- batch or smooth non-urgent traffic where possible
- avoid unnecessary polling when webhooks or event-driven patterns are available

## Notes

Older onboarding or quickstart material may describe prior defaults. This page is the authoritative source for current standard limits unless a contract states otherwise.
