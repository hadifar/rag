# User Roles and Permissions

AtlasFlow uses role-based access at the workspace level. Some actions are additionally constrained by project-specific permissions, but the workspace roles below define the baseline capabilities.

## Workspace roles

- Workspace Owner
- Admin
- Member
- Billing Admin
- Viewer

## Role descriptions

### Workspace Owner
The Workspace Owner has full control over the workspace.

Owners can:

- manage workspace settings
- manage billing settings
- invite, deactivate, and remove users
- manage integrations
- configure SSO
- create workspace API keys
- view audit and administrative activity
- transfer ownership to another eligible user

There must always be at least one Workspace Owner.

### Admin
Admins can manage most operational and technical aspects of the workspace, but they are not the commercial owner of the account unless they also hold billing access.

Admins can typically:

- manage workspace settings
- invite and manage users
- manage integrations
- configure SSO
- create workspace API keys
- create and edit workflows and dashboards
- view administrative logs according to plan limits

Admins cannot transfer workspace ownership.

### Member
Members are standard working users.

Members can typically:

- access assigned projects and workflows
- create and edit workflows where project permissions allow it
- run workflows
- view dashboards they have been granted access to
- create personal API keys where API access is enabled

Members cannot:

- change workspace-wide settings
- manage SSO
- manage integrations at the workspace level
- create workspace API keys
- manage billing

### Billing Admin
Billing Admin is a limited administrative role intended for finance or procurement contacts.

Billing Admins can:

- view invoices
- update payment methods
- manage billing contacts
- view subscription details
- download billing documents

Billing Admins cannot, by role alone:

- change general workspace settings
- manage SSO
- manage integrations
- create workspace API keys
- invite or remove users

If a person needs both billing capabilities and broader product administration, they must also have another appropriate role such as Admin or Workspace Owner.

### Viewer
Viewers have read-only access to the content they are allowed to see.

Viewers can typically:

- view projects, workflows, and dashboards they have been granted access to
- manually export data where export permissions allow it

Viewers cannot create or edit workflows, change settings, manage users, or manage billing.

## Permissions for common administrative actions

### Manage integrations
Allowed roles:
- Workspace Owner
- Admin

### Configure SSO
Allowed roles:
- Workspace Owner
- Admin

### View and update billing details
Allowed roles:
- Workspace Owner
- Billing Admin

### Create personal API keys
Allowed roles:
- Workspace Owner
- Admin
- Member

### Create workspace API keys
Allowed roles:
- Workspace Owner
- Admin

## Notes

Some organizations keep finance contacts as Billing Admin without giving them day-to-day workspace administration access. That is expected behavior and is the main reason Billing Admin is separate from Admin.
