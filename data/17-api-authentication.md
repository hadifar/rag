# API Authentication

AtlasFlow API requests must be authenticated using a valid bearer token.

## Supported token sources

AtlasFlow supports two main token sources:

- personal API keys
- workspace API keys

## Bearer token usage

Requests should include the token in the `Authorization` header using the standard bearer format.

Example pattern:

`Authorization: Bearer <token>`

## Personal API keys

A personal API key acts on behalf of the user who created it.

Implications:

- access is limited by that user’s permissions
- removing or reducing the user’s permissions changes what the token can do
- revoking the key immediately invalidates future requests

## Workspace API keys

A workspace API key is designed for shared integrations.

Implications:

- it is managed at the workspace level
- it is not tied to a single employee identity in the same way as a personal key
- it is appropriate for automation services that should not depend on one person’s account

Workspace API keys are available on Growth and Enterprise.

## Revocation behavior

When a key is revoked:

- new requests using that token fail immediately
- there is no grace period for continued use

## Common authentication errors

### 401 Unauthorized
Common causes:

- missing token
- malformed bearer header
- revoked key
- expired key

### 403 Forbidden
Common causes:

- token is valid, but the caller lacks permission for the requested resource
- the request attempts an action reserved for a higher-privilege role
- the token is valid for a different scope than the requested operation

## Best practice

- use personal keys for user-owned automation
- use workspace keys for shared services
- avoid embedding tokens in client-side code
- revoke and rotate credentials promptly when operational ownership changes
