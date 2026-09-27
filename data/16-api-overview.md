# API Overview

AtlasFlow provides a REST API for common workspace, workflow, reporting, and integration use cases.

## Common API use cases

Customers use the API to:

- start workflows
- read workflow run status
- list projects and users
- export operational data
- connect AtlasFlow to internal tools and services

## Authentication model

AtlasFlow API requests use bearer-token authentication. The exact token type depends on whether the caller is using a personal API key or a workspace API key.

See the authentication documentation for details.

## Resource areas

Common API resource groups include:

- workspaces
- projects
- workflows
- workflow runs
- users
- reports
- integrations

Availability of particular endpoints may depend on plan or product module availability.

## Pagination

List endpoints typically use cursor-based pagination.

A typical paginated response includes:

- an array of items
- a next cursor when more results exist

Clients should not assume that a single request will return the full result set for large workspaces.

## Error format

API errors generally return a structured JSON body including values such as:

- error code
- message
- request identifier

Typical HTTP status codes include:

- 400 for malformed requests
- 401 for missing or invalid authentication
- 403 for authenticated requests without sufficient permission
- 404 for resources not found or not visible to the caller
- 429 for rate-limit enforcement
- 5xx for platform-side failures

## Plan notes

API access is available on all paid plans, but capabilities differ by plan. For example, workspace-scoped credentials and webhook-based integration patterns are not available on every plan.
