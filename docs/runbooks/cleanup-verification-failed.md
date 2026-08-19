# Runbook: cleanup verification failed or missing

**Severity:** SEV-0 if a later tenant may have started; otherwise SEV-1

**Trigger:** failed/invalid/missing cleanup receipt, receipt/job mismatch,
canary recovery, orphan environment, GPU reset failure, or quarantine latency
over 60 seconds.

## Contain

1. Confirm the node is quarantined and cannot claim. If central state is
   uncertain, disable the affected node and workload tier at the scheduler.
2. Stop lease renewal and prevent reassignment that could create duplicate work.
3. Revoke node and per-job transfer capabilities; destroy the job DEK if the
   key authority has not already done so.
4. If any later tenant ran after the failed boundary, declare SEV-0 and invoke
   `suspected-data-exposure.md`.
5. Do not ask the provider to keep using the machine. Ask them to leave it
   powered on and disconnected from marketplace work pending scoped guidance.

## Investigate

- Verify receipt signature, enrolled key, job/node aliases, timestamps and
  replay state without copying customer content.
- Determine the first failed step: process tree, key, volume, temp path, GPU,
  network policy, orphan scan or canary.
- Enumerate opaque VM/volume/switch/device identifiers from the supervisor.
- Check whether sleep, restart, power loss, agent update or security-software
  interference overlapped cleanup.
- Bound every job admitted since the last verified cleanup and every storage/key
  capability issued to the node.

## Recover

Destroy remaining runtime objects from a trusted recovery environment. Reset or
reboot the GPU/host when vendor procedure requires it. Run a fresh synthetic
audit that plants and attempts to recover markers and verifies host integrity,
agent/image attestation, storage and network policy. Rotate node identity if
the supervisor/signing key could be compromised.

Quarantine is cleared only through the privileged operator workflow after all
checks pass and the incident commander records the evidence ID. Restarting or
re-registering must not clear it.

## Close

Verify zero affected nodes can claim while quarantined, terminal/receipt counts
reconcile, no marker is recovered, and alert routing worked. A cleanup failure
caused by a repeatable code/device defect blocks that runtime/image/device class
until remediated and retested.
