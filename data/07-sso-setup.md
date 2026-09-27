# SSO Setup

AtlasFlow supports SAML-based Single Sign-On (SSO) on **Growth** and **Enterprise** plans.

This guide explains the high-level setup process and key operational rules.

## Who can configure SSO

Only the following roles can configure SSO:

- Workspace Owner
- Admin

## Prerequisites

Before SSO can be enforced, the workspace must meet the following prerequisites:

- the workspace must be on Growth or Enterprise
- a supported SAML identity provider configuration must be available
- the relevant company domain must be verified
- at least one administrator should retain fallback local login access for recovery purposes

## Recommended setup sequence

1. Gather identity provider metadata and certificate details.
2. Open the AtlasFlow SSO settings page.
3. Configure the SAML connection.
4. Verify the organization domain.
5. Test SSO with a small admin group.
6. Confirm login behavior for affected users.
7. Enable enforcement only after successful testing.

## Domain verification

**Domain verification is required before SSO enforcement can be enabled.**

Verification confirms that the workspace administrator controls the domain that will be associated with SSO login behavior.

Without verified domain ownership, AtlasFlow allows configuration work but does not allow SSO enforcement.

## Fallback access

AtlasFlow strongly recommends keeping at least one administrator able to sign in with a local AtlasFlow password.

This fallback account is important in case:

- the identity provider configuration changes unexpectedly
- certificate rotation is incomplete
- login testing reveals a misconfiguration
- a user cannot complete SSO due to domain mismatch or rollout timing

## Enforcement behavior

When SSO is enforced for a verified domain:

- users on that domain are expected to authenticate through SSO
- direct local password login may be blocked for those users
- users outside the enforced domain are not automatically affected unless configured otherwise

## Common issues

Frequent causes of SSO-related login problems include:

- domain not verified
- incorrect identity provider metadata
- certificate mismatch
- user email domain not matching the verified domain
- SSO enforced before testing fallback access

## Notes

This guide covers authentication setup only. It does not describe every possible identity lifecycle option or contract-specific implementation detail.
