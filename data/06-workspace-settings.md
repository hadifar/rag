# Workspace Settings

Workspace settings control shared behavior across AtlasFlow for a given workspace.

Only Workspace Owners and Admins can manage general workspace settings unless otherwise stated.

## Main settings areas

### General
General settings include the workspace name, default language behavior where available, and basic organization details.

### Time zone
The workspace time zone is used as the default reference for:

- workflow due dates
- scheduled runs
- dashboard date grouping
- scheduled report exports
- audit display timestamps in the web interface

Individual users may see some timestamps localized in the interface, but workspace-wide automation behavior uses the workspace setting unless a feature explicitly states otherwise.

### Branding
Branding settings may include:

- logo
- accent color
- sender name for certain outbound notifications
- customer-facing label choices in shared reports where supported

### Notifications
Workspace-level notification settings define defaults for:

- digest behavior
- workflow event notifications
- reminder behavior
- certain administrative notification defaults

Users can still override some notification preferences at the user level, depending on the type of notification.

### Archival behavior
Workspace Owners can archive a workspace when it should no longer be used operationally but should remain retained for later reference or controlled restoration.

Archiving a workspace is different from deleting it.

Archiving generally:

- prevents normal operational use
- preserves historical information subject to retention policies
- allows controlled restoration by authorized administrators

### Retention defaults
Workspace settings may display plan-dependent retention defaults, but the authoritative source for retention periods and purge behavior is the data retention policy.

## Common administrative uses

Workspace settings are commonly used when:

- a company changes branding
- a region or business unit needs a different time zone
- notification volume needs to be reduced by default
- an old workspace should be retired without immediate deletion

## Notes

Workspace settings do not replace billing administration, SSO setup, or detailed retention policy configuration. Those topics have their own dedicated documentation and, in some cases, separate permission requirements.
