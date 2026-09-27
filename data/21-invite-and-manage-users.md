# Invite and Manage Users

This guide explains how user access is typically managed in AtlasFlow.

## Inviting users

Workspace Owners and Admins can invite users to a workspace.

An invitation generally includes:

- the recipient email address
- the assigned workspace role
- any initial project access where relevant

## Pending invites

Pending invites remain outstanding until the user accepts them or the invite expires.

Standard behavior:

- pending invites can be re-sent
- sending a new invite invalidates the old invite link
- an invite that is too old may need to be reissued rather than reused

## Deactivate vs remove

AtlasFlow distinguishes between deactivating a user and removing their workspace access.

### Deactivate
Deactivation prevents the user from actively using the workspace.

Typical reasons to deactivate a user:

- temporary leave
- internal suspension
- staged offboarding while preserving administrative context

### Remove access
Removing access removes the user from the workspace’s active access model.

Typical reasons:

- permanent departure
- moving the user to another workspace only
- cleanup after an incorrect invitation

## Historical records

Historical actions such as workflow assignments, approvals, and run history are generally preserved for audit and operational continuity even after a user is deactivated or removed.

## Why someone might still receive communication

Changing workspace access does not always stop every type of message immediately.

Possible reasons include:

- a queued digest or reminder was already generated
- the user remains a billing or administrative contact
- another linked communication rule still targets that address

If email continues unexpectedly, also review the email notification and billing guidance documents.
