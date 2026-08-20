# Runbook: suspected sandbox escape

**Severity:** SEV-0

**Trigger:** guest reaches host/provider LAN/another tenant, unexpected host
process or startup mutation, hypervisor/GPU escape indicator, attestation drift,
or escape canary succeeds.

1. Globally stop new claims for the affected workload/image/runtime/device
   class. Quarantine every node that ran it; do not rely on the suspected host
   to enforce containment.
2. Revoke node and transfer credentials, expire leases, isolate hosts from the
   marketplace network, and prevent artifact distribution from affected jobs.
3. Invoke `suspected-data-exposure.md` if customer/provider data may have crossed
   a boundary. Notify founder, R4/R10, runtime owner and counsel.
4. Preserve central content-free attestation, receipt, network, image and access
   evidence. Do not instruct an untrained provider to explore malware or upload
   disk/memory images containing personal data.
5. Bound vulnerable image/runtime/GPU/driver versions and jobs. Check vendor
   advisories and whether the same boundary protects other workload tiers.
6. Rebuild, do not “clean,” a confirmed compromised host. Rotate its keys and
   credentials and require new enrollment/attestation.
7. Re-enable only after patched signed images/runtime, regression/adversarial
   suite, canary tests and independent retest pass. Critical escape remediation
   target is 48 hours; keep the affected tier disabled if that target cannot be
   met.
