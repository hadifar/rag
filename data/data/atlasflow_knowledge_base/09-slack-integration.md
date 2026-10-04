# Slack Integration

AtlasFlow integrates with Slack to help teams receive alerts, review activity, and act on workflow items without leaving Slack.

## What the Slack integration can do

Depending on plan and configuration, the Slack integration can be used to:

- send workflow notifications to channels
- send direct messages for assigned work
- post approval requests
- send reminders for overdue items
- send automation failure notifications

## Plan availability

### Starter
Starter supports Slack notifications such as:

- channel notifications
- direct message notifications
- reminder messages

Starter does **not** support interactive Slack approval actions.

### Growth
Growth supports:

- notifications
- direct messages
- reminder messages
- **interactive Slack approval actions**

### Enterprise
Enterprise supports the same Slack approval capabilities as Growth, along with any contract-specific operational controls.

## Permissions and setup

Slack integration setup requires:

- a Workspace Owner or Admin
- authorization of the Slack workspace
- selection of the destination channels or allowed message patterns
- confirmation that the installing user has the required Slack permissions

## Channels vs direct messages

### Channels
Channel notifications are useful for shared visibility, team alerts, and exception monitoring.

### Direct messages
Direct messages are useful for personal reminders, assigned approvals, or user-specific action requests.

## Common limitations

- approval actions are unavailable on Starter
- a user may receive Slack notifications only if the integration is installed and the workspace settings allow the notification type
- channel delivery depends on the channel still existing and the app still being authorized
- direct message behavior depends on the Slack user mapping remaining valid

## Common troubleshooting checks

If Slack-based actions stop working, check:

- whether the Slack app is still authorized
- whether the relevant channel still exists
- whether the workflow is paused
- whether the workspace plan includes the requested capability
- whether a reconnect changed the available permissions
