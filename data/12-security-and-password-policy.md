# Security and Password Policy

_Last updated: 2026-01-20_

This document describes the baseline security practices and password requirements for AtlasFlow workspaces using local authentication.

## Password requirements for local login

For workspaces that allow direct AtlasFlow password login, user passwords must meet the following minimum requirements:

- at least 12 characters
- at least one letter
- at least one number

Customers may use stronger internal policies, but the above is the baseline enforced by AtlasFlow for local-auth workspaces.

AtlasFlow recommends passphrases over short complex passwords.

## Password resets

Password reset links are time-limited and intended for one-time use. If a user requests multiple resets, only the most recent valid link should be used.

## MFA recommendation

AtlasFlow strongly recommends enabling multi-factor authentication where available, especially for administrative users and workspaces that do not enforce SSO.

For workspaces using SSO, MFA behavior may be governed by the identity provider rather than AtlasFlow directly.

## Session behavior

Default session handling may include inactivity and re-authentication controls appropriate to the plan and workspace configuration. Security-sensitive actions may require re-authentication even within an active session.

## API key handling

API keys should be treated as sensitive credentials.

Recommended practices:

- store keys in a secure secret manager
- do not paste keys into shared documents or tickets
- rotate keys regularly
- revoke keys that are no longer needed
- use workspace keys only for shared integrations and personal keys only for user-owned automation

## Least-privilege principle

Workspace administrators should assign the minimum role necessary for a user or system to perform its function.

Examples:

- use Billing Admin rather than Admin for finance-only access
- avoid long-lived shared credentials unless operationally necessary
- review administrative roles regularly
