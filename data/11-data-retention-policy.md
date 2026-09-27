# Data Retention Policy

_Last updated: 2026-02-03_

This policy defines the standard retention behavior for AtlasFlow workspace data. Where a customer has contract-specific retention terms, those terms supersede the defaults described here.

## 1. Workflow run data

Workflow run data includes run metadata, step status, timestamps, and other operational execution records.

Default retention by plan:

- **Starter:** 90 days
- **Growth:** 365 days
- **Enterprise:** configurable by contract

Unless otherwise agreed in writing, Enterprise workspaces use a 365-day default for workflow run data.

## 2. Audit event history

Audit event history includes administrative and security-relevant workspace actions such as configuration changes, login events exposed by the plan, role changes, and key management events where supported.

Default audit event visibility by plan:

- **Starter:** 30 days
- **Growth:** 180 days
- **Enterprise:** 365 days by default, with contract-based extension options

This section is the authoritative source for audit history retention. Summary pages may simplify this information.

## 3. Archived workspaces

Archiving a workspace does not immediately purge its historical data.

Archived workspaces remain retained according to the applicable data retention and contractual rules unless they are later scheduled for deletion.

## 4. Deleted workspaces

When a workspace is deleted, it enters a **30-day recovery window** before permanent purge.

During this window:

- the workspace is not available for normal operational use
- restoration may be possible through authorized support or administrative recovery paths
- permanent purge is deferred until the recovery window ends

After the recovery window ends, AtlasFlow proceeds with permanent deletion according to internal purge processes and any applicable contractual obligations.

## 5. Exports and downstream copies

Data exported by a customer from AtlasFlow is no longer governed by AtlasFlow retention once it has been successfully delivered outside the platform. Customers are responsible for their own handling of exported data.

## 6. Contractual overrides

Enterprise customers may have contract-specific retention commitments covering one or more of:

- workflow run data
- audit event history
- backup retention
- regional storage guarantees

Where such terms exist, contract terms prevail over the defaults in this document.
