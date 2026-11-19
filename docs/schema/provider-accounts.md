# Provider account and enrolment schema

This is the schema design for [ADR 0005](../adr/0005-provider-accounts-and-agent-enrolment.md) and tasks Y6–Y8. The schema adds provider accounts, sessions, one-time keys and durable node credentials.

## Account and session tables

| Table | Columns | Constraints and indexes |
|---|---|---|
| `provider_accounts` | `provider_account_id TEXT`, `email TEXT`, `password_hash TEXT`, `display_name TEXT`, `created_at TIMESTAMPTZ`, `last_login_at TIMESTAMPTZ` | Primary key on the account ID, unique normalised email, creation time defaults to `now()`. Display name and last login are nullable. |
| `provider_sessions` | `session_id TEXT`, `provider_account_id TEXT`, `token_hash TEXT`, `created_at TIMESTAMPTZ`, `expires_at TIMESTAMPTZ`, `revoked_at TIMESTAMPTZ` | Primary key on the session ID, owning account FK with deletion cascade, unique token digest and an index on account plus creation time. Revocation is nullable and creation time defaults to `now()`. |

All columns are required unless marked nullable. A session expires at `expires_at` and becomes invalid immediately when `revoked_at` is set. The account and session are written in one transaction at signup. Provider and customer emails can coincide, with each session usable only in its own realm. Both signup routes honour `SIGNUPS_OPEN`. An operator can seed a provider account on a closed instance.

## Enrolment and machine ownership

| Record | Purpose |
|---|---|
| `provider_enrolment_keys` | Account ID, key ID, prefix and unique digest, plus timestamps for creation, expiry, redemption and revocation. The account and creation time are indexed. |
| `provider_node_credentials` | One row per enrolled node ID. Stores its owner, the current credential digest, issuance time and optional revocation time. The digest is unique. The owner is indexed. |
| `provider_nodes` | Hardware, heartbeat and eligibility. Operator flags for inference and render default to false. Pre-enrolment rows can retain their existing telemetry. |

The credential table owns the relationship between node and provider. A nullable duplicate on the telemetry table would create two places to change ownership. This layout also lets an authenticated machine recreate a missing telemetry row while retaining its owner and credential. The recreated telemetry row needs fresh work approval.

A key expires after 15 minutes. The create response includes the secret once. Redemption locks the key and binds ownership in one transaction. An ownership conflict rolls back key consumption. A provider can re-enrol its own machine with a new key after a lost response or revoked credential. Re-enrolment replaces the credential and clears both workload approvals. Another account cannot reassign an owned node. Inference jobs queued before the current credential was issued are ineligible for that credential.

Registration refreshes telemetry with the current node credential. The old token digest column can authenticate telemetry from an existing legacy row until enrolment clears it. New claims require an authenticated enrolled node with current telemetry and approval for the requested workload. Revocation and claims lock the same credential row. Work already delivered before revocation may still be running on the machine.

## Rollout

1. Test the schema upgrade against the previous database, then test enrolment, reboot, revocation and re-enrolment with the replacement Windows build on staging.
2. The current released Windows agent still calls anonymous registration on startup. The development desktop sends an authenticated registration and uses the OS-backed credential interface. Coordinate the API and agent cutover after the maintainer implements the store under ADR 0002 and verifies the packaged build on Windows.
3. Approve inference only for the controlled pilot machine after verifying its owner. Use the [pilot operator command](../PROVIDER-APP.md#approve-or-pause-pilot-inference). Rendering approval remains a separate operator decision for owner-controlled hardware.
4. When recovering from an older backup, reconcile revocation and approval changes before opening the queue. If a credential row is absent from the backup, issue a fresh enrolment key from the owning account. Ownership transfers and duplicated machine IDs require operator reconciliation.
