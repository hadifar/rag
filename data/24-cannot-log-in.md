# Cannot Log In

This guide covers common AtlasFlow login issues.

## 1. Local login vs SSO confusion

If the workspace uses SSO and the user belongs to a verified and enforced domain, direct password login may no longer work for that user.

Ask:

- is SSO enabled for the workspace?
- is SSO enforcement active?
- is the user’s email on the enforced domain?

## 2. Domain mismatch

A user may attempt SSO with an email address that does not match the verified domain expected by the workspace configuration.

This often happens when:

- a personal email is used instead of a work email
- the user changed company domains
- the workspace was configured for one domain but the user is authenticating under another

## 3. Expired invite

If the user has never completed access setup, the invite may simply be old or invalid.

In that case:

- re-send the invite
- ensure the latest invite link is used
- verify the user is entering the expected email address

## 4. Password reset issues

For workspaces that still allow local login, password reset failures are often caused by:

- using an older reset link after a newer one was requested
- opening an expired link
- attempting local login when SSO is now enforced

## 5. Fallback admin access

If SSO was enabled recently and many users cannot sign in, check whether a fallback local admin account still exists. This is one reason AtlasFlow recommends keeping at least one local admin recovery path available.

## What support will usually ask for

To troubleshoot efficiently, support typically needs:

- workspace name or identifier
- affected user email
- whether the user previously signed in successfully
- approximate time of the failed attempt
- screenshot or text of the error shown
- whether SSO enforcement was changed recently
