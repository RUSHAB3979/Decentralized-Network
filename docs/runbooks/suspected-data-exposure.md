# Runbook: suspected customer-data exposure

**Severity:** SEV-0

**Trigger:** cross-tenant canary, customer content/secret in telemetry, provider
reports retained data, unauthorized object/key access, or cleanup bypass with
possible later reuse.

## Contain first

1. Assign incident commander and page founder, R4, R10, affected system owner
   and retained counsel/legal contact.
2. Disable affected nodes, image/runtime version and workload class. Preserve
   unaffected capacity only if the boundary is demonstrably independent.
3. Revoke node tokens, session/transfer capabilities and affected credentials;
   disable object access and destroy remaining per-job DEKs where safe.
4. Stop log/export pipelines containing suspected data and restrict access. Do
   not delete evidence or spread it into chat, tickets, dashboards or local PCs.

## Scope

Using opaque IDs and access-controlled systems, bound: earliest/latest UTC,
data class, affected jobs/customers/providers, storage objects/key versions,
nodes/images/runtime versions, who accessed it, and whether exfiltration is
confirmed or only possible. Preserve original audit/storage/access logs with
integrity hashes and documented custody. Never collect more customer content
than counsel/forensic lead approves.

## Eradicate and recover

Patch/disable the cause; rotate credentials/keys; purge unauthorized copies
under legal direction; rebuild compromised components from signed images; run
isolation, cleanup and canary regression tests; and obtain independent retest
for a boundary failure. Re-enable one bounded pool first with intensified
content-free monitoring.

## Communications

Only the designated incident communicator contacts customers/providers/public.
State known facts, protection steps and next update time; do not speculate about
attacker identity or say “no breach” before investigation. Counsel determines
whether personal-data/breach notification duties and timelines apply.

## Close

Record decision/evidence IDs, affected population methodology, notification
decision, rotations/deletions, independent verification and preventive actions.
Safety-invariant work remains frozen until R4 and the incident commander accept
the remediation evidence.
