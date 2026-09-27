# Jira Integration

AtlasFlow integrates with Jira for teams that need operational workflows and engineering issue tracking to work together.

## Common use cases

Typical Jira integration use cases include:

- creating Jira issues from AtlasFlow workflow steps
- linking operational exceptions to Jira tickets
- reflecting selected Jira status updates back into AtlasFlow
- escalating failed workflow steps into an engineering backlog

## Sync direction

The integration supports targeted synchronization rather than unrestricted full-field two-way sync.

Common supported patterns include:

- AtlasFlow -> Jira issue creation
- AtlasFlow -> Jira field updates for mapped fields
- Jira -> AtlasFlow status or comment updates for linked items where configured

Customers should not assume that every Jira field is editable in both directions.

## Permissions

Setup typically requires:

- a Workspace Owner or Admin in AtlasFlow
- an authorized Jira connection with the required scopes
- access to the relevant Jira project(s)

## Field mapping notes

Field sync depends on explicit mapping.

Common caveats:

- custom Jira fields may require manual mapping
- renamed or deleted Jira fields can break sync behavior
- reconnecting the integration may require project or field mappings to be reviewed again

## Operational limitation

If a workflow step depends on Jira and the Jira connection is reauthorized with different scopes, previously working automations may fail until the integration mapping is refreshed.

## Troubleshooting checks

If Jira-related workflow steps stop working, check:

- whether the Jira connection is still active
- whether project mappings still point to valid Jira projects
- whether required fields changed in Jira
- whether the workflow is using an outdated draft configuration instead of the current published version
