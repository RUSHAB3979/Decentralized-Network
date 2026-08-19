# Runbook: object deletion or retention failure

**Severity:** SEV-1; SEV-0 if unauthorized access or cross-customer exposure is
observed

**Trigger:** source/artifact survives enforced expiry, deletion API fails,
inventory diverges from terminal jobs, expired capability still works, or
backup maximum age is exceeded.

1. Stop issuing new capabilities to the affected bucket/prefix and pause
   affected submissions. Revoke storage credentials and outstanding
   capabilities where the backend permits.
2. Preserve inventory/access/lifecycle evidence using object aliases, versions,
   sizes and timestamps only. Do not download customer objects for diagnosis.
3. Determine whether the fault is policy missing/disabled, permission denial,
   versioning/delete markers, replication, object lock, backup, provider outage,
   or control-plane state mismatch.
4. Destroy per-object/per-job keys to achieve crypto-erasure when designed and
   safe. Execute bounded deletion, including versions/replicas, through the
   approved storage tool and capture result IDs.
5. If any access occurred after intended expiry or isolation failed, invoke
   `suspected-data-exposure.md`.
6. Reconcile all terminal jobs against storage/key inventory before restoring
   issuance. Add an automated lifecycle/inventory check for the missed case.
