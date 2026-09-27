# Email Notifications

AtlasFlow uses email notifications for workflow activity, reminders, exports, administrative events, and billing-related communication.

## Types of email notifications

Common email categories include:

- workflow assignments
- approval requests
- overdue reminders
- export delivery notices
- administrative notices
- invoice and renewal notices

## Workspace defaults vs user preferences

AtlasFlow supports two layers of notification behavior:

### Workspace-level defaults
Workspace Owners and Admins can configure default notification behavior for the workspace. This is useful for setting the initial level of email noise for new users.

### User-level preferences
Individual users can change certain notification settings for themselves, such as digest versus real-time delivery where supported.

Not every email category is user-optional. Some administrative and billing messages are governed by workspace or account-level rules rather than user preference alone.

## Digest vs real-time behavior

For supported notification types, delivery may be configured as:

- real-time
- daily digest
- weekly digest

The available options depend on the event type and workspace configuration.

## Role changes and delayed delivery

In some cases, a user may continue receiving email briefly after their role changes or access is removed.

This can happen because:

- a notification was already queued before the access change
- a digest had already been prepared for delivery
- the user remains a designated billing or administrative contact for a communication category

Queued messages are not always canceled retroactively.

## Billing and administrative contacts

A person may stop being an active workspace user and still continue receiving certain invoice, renewal, or administrative messages if they remain the configured contact for those categories.

If those messages should stop, the contact should be updated in billing or workspace settings as appropriate.

## Common troubleshooting questions

If someone is receiving email unexpectedly, check:

- their personal notification preferences
- workspace-level defaults
- whether the message was already queued
- whether they are still listed as a billing or administrative contact
- whether the workspace access change happened after the relevant event was already triggered
