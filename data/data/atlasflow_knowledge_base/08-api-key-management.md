# API Key Management

AtlasFlow supports API access using bearer tokens generated from API keys.

There are two key types:

- personal API keys
- workspace API keys

## Personal API keys

Personal API keys are tied to an individual user account.

Characteristics:

- inherit the permissions of the user who created them
- are appropriate for user-scoped automation or development work
- are available to eligible users on all paid plans where API access is enabled

In general, the following roles may create personal API keys:

- Workspace Owner
- Admin
- Member

A Billing Admin or Viewer cannot create a personal API key unless they also hold another eligible role.

## Workspace API keys

Workspace API keys are intended for shared system-to-system integrations.

Characteristics:

- belong to the workspace rather than one named user
- are managed centrally
- are appropriate for server-side integrations and automation services

Workspace API keys are available on:

- Growth
- Enterprise

Workspace API keys can be created by:

- Workspace Owner
- Admin

## Expiration and rotation

When supported by the workspace configuration, keys may be created with expiration periods such as:

- 30 days
- 90 days
- 180 days
- no fixed expiration

AtlasFlow recommends rotating keys regularly and using the shortest practical lifetime for the use case.

## Secret visibility

For security reasons, the full secret value is shown only at creation time.

After that point:

- the key may remain listed in the UI
- metadata such as name, creator, and last-used timestamp may remain visible
- the full secret cannot be viewed again

If the secret is lost, the correct action is to create a new key and revoke the previous one.

## Revocation

Revoking a key invalidates it immediately for future authentication attempts.

Revocation is recommended when:

- a key was shared insecurely
- a system using the key has been retired
- a credential may have been exposed
- the integration owner has changed

## Best practices

- use personal keys only for user-owned workflows
- use workspace keys for shared services
- rotate keys regularly
- store keys in a secure secret manager
- avoid embedding keys in client-side code
