# Security and reliability control set

**Owners:** R4 Security & Sandbox Engineer and R10 Site Reliability Engineer,
as defined in [`docs/ROLES.md`](../ROLES.md).

**Status:** security contract and operating design implemented; production OS
sandbox integration and cross-team control-plane changes remain gated work.

This directory is the normative security design for running customer workloads
on provider-owned hardware. The executable, dependency-free contract lives in
[`security/runtime_contract.py`](../../security/runtime_contract.py).

## Non-negotiable claims

1. A provider node is untrusted. A process running on that host cannot keep a
   secret from an administrator with physical or kernel access. Encryption at
   rest and cleanup reduce retained data; they do not make plaintext invisible
   while it is being computed.
2. Customer-supplied `.blend` files and interactive game workloads execute only
   in a disposable full VM with a dedicated/pass-through GPU, default-deny
   networking, resource limits, and verified cleanup. Windows Sandbox,
   containers, and WSL2 are not the sole hostile-file boundary.
3. A node cannot claim a second tenant's job without a verified cleanup receipt
   for the first. Missing, malformed, stale, or failed evidence quarantines it.
4. Security telemetry is content-free. It never contains prompts, outputs,
   customer identifiers, filenames, paths, IP addresses, hostnames, tokens, or
   stable hardware identifiers.
5. `render_eligible` is an administrative pilot gate, not a sandbox. It remains
   false for third-party nodes until the exit gates in the sandbox design pass.

## Workload tiers

| Tier | Permitted data | Required boundary |
|---|---|---|
| Observed | synthetic benchmarks and canaries only | monitored agent; no customer data |
| Vetted inference | customer inference after explicit risk acceptance | signed agent/image, encrypted disk, attestation, current audit |
| Isolated | untrusted render and cloud gaming | disposable full VM, dedicated GPU, deny-by-default network, verified destruction |

Vetted inference still exposes in-use prompt and response plaintext to a
malicious host administrator. Confidential workloads requiring protection from
the provider must wait for independently evaluated confidential-computing
hardware or remain on platform-controlled supply.

## Documents

- [T01/T04 threat model](../risk/threat-model-t01-t04.md)
- [Untrusted Blender threat model](../risk/threat-model-untrusted-blend.md)
- [Render sandbox design](render-sandbox-design.md)
- [Runtime and cleanup contract](runtime-contract.md)
- [Data lifecycle and private identity](data-lifecycle-and-identity.md)
- [CI security audit](ci-security-audit.md)
- [External penetration-test scope](external-penetration-test-scope.md)
- [Cross-team implementation handoffs](cross-team-handoffs.md)
- [SRE objectives and alerts](../sre/objectives-and-alerts.md)

## Stop-ship conditions

- Any third-party render node is marked eligible before the isolation exit
  gates pass.
- A provider can register or claim customer work without authenticated,
  authorized node identity.
- A cleanup failure does not automatically prevent the next claim.
- Production billing uses self-reported runtime before trusted metering exists.
- A source object, prompt payload, result, or per-job encryption key has no
  enforced terminal-state deletion policy.
- A release contains a known critical sandbox escape without a deployed
  mitigation. Critical sandbox/runtime CVEs have a 48-hour remediation SLA;
  affected workload tiers are disabled when that cannot be met.

## Verification

Run the security-owned tests without installing project dependencies:

```bash
python3 -m unittest discover -s security/tests -v
```

Passing these tests proves only the policy state machine and receipt validation.
It does not prove an OS, hypervisor, storage backend, GPU, or provider device is
secure. Those claims require the integration tests and independent assessment
specified in the penetration-test scope.
