# Exporting Reports

This guide explains how to export dashboards and reports from AtlasFlow.

## Supported export formats

AtlasFlow supports the following common export formats:

- CSV
- XLSX
- PDF

The available format depends on the dashboard or report type.

## Manual export

Manual export is available on all plans to users who both:

- can access the dashboard or report
- have permission to export from that view

Typical manual export flow:

1. Open the dashboard or report.
2. Apply the desired filters.
3. Select the export option.
4. Choose the format.
5. Wait for the export to complete or be delivered.

## Scheduled export

Scheduled exports are available on **Growth** and **Enterprise** only.

Typical scheduled export flow:

1. Open the dashboard or report.
2. Confirm that the workspace plan supports scheduled exports.
3. Choose a frequency such as daily, weekly, or monthly.
4. Set recipients or the configured destination.
5. Save the schedule.

## Common failures

Frequent export issues include:

- the user lacks access to the dashboard
- the workspace is on Starter and the user is trying to create a schedule
- filters return too much data, causing long generation times
- recipients are no longer valid
- the dashboard definition changed after the schedule was created

## Permissions

In general:

- users with access may perform manual exports where allowed
- creating or changing scheduled exports typically requires a role with edit or administrative permission for the report configuration

## Tips

If an export fails:

- verify the plan allows the requested export type
- confirm the dashboard still exists
- verify recipient addresses for scheduled delivery
- retry with a narrower date range if the export is very large
