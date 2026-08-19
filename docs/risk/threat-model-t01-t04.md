# Threat model: T-01 provider data theft and T-04 sandbox escape

**Owner:** R4 Security & Sandbox Engineer

**Reviewed against repository:** 2026-08-20

**Assets:** customer prompts, responses, source files, render artifacts, model
weights, provider host/credentials/LAN, platform control plane, and audit proof.

## Trust boundaries

The customer trusts the platform but not the provider. The provider trusts the
platform but not the customer workload. The provider host OS, its administrator,
firmware, drivers, and physical memory are outside the trusted computing base.
The sandbox boundary protects the provider from the workload; it cannot by
itself protect workload plaintext from a malicious host administrator.

The current Python agent executes inference and Blender on the provider host.
Blender uses `--disable-autoexec` and temporary directories, but there is no
full VM, default-deny network, GPU reset proof, attestation, or crash-durable
cleanup receipt. These controls are therefore design requirements, not claims
about the current runtime.

## T-01 — data theft from a provider node

### Attack tree

Goal: obtain or retain one tenant's data.

1. Become or compromise a provider.
   1. Register a fake node while provider enrollment is unauthenticated.
   2. Steal the plaintext node token from the provider filesystem.
   3. Modify the agent or worker image and report attractive capabilities.
2. Observe data in use.
   1. Instrument the host process, driver, kernel, swap, RAM, or VRAM.
   2. Capture presigned URLs or intercept plaintext after the guest decrypts it.
   3. Read prompts or results from a host-visible process boundary.
3. Recover data after completion.
   1. Copy temporary source/output files before best-effort deletion.
   2. Recover blocks from an unencrypted or persistent volume.
   3. Recover buffers from VRAM or a reused VM/process.
   4. Force sleep, power loss, or agent crash before graceful cleanup.
4. Correlate identities.
   1. Collect customer IP addresses through future direct P2P/ICE paths.
   2. Expose stable provider hardware identifiers publicly.
   3. Place customer IDs, model inputs, paths, or URLs in logs and metrics.
5. Exfiltrate.
   1. Use unrestricted outbound network or the provider LAN.
   2. Hide data in artifacts, receipts, logs, crash dumps, or telemetry.

### Controls and load-bearing control

The controls are: authenticated node enrollment; signed/attested agent and
curated image digests; minimal encrypted job envelopes; a unique encrypted
ephemeral volume and key per job; no host mounts; default-deny egress; dedicated
GPU assignment; process/VM destruction; key and volume destruction; GPU cleanup;
synthetic canary recovery tests; content-free signed receipts; and automatic
quarantine on missing evidence.

The load-bearing confidentiality control for retained data is destruction of
the per-job data-encryption key outside the provider-controlled host, followed
by destruction of the ephemeral volume. If that key remains available, deleting
files is not a reliable wipe on SSDs. If this control fails, the node is
quarantined, relevant keys/storage are disabled, and the event is handled as a
suspected data exposure.

It is not a control for data *in use*. On ordinary consumer GPUs, plaintext must
be available to software or the accelerator. A malicious host can capture it.
Tier assignment and customer disclosure must preserve this residual risk.

### Detection

- Admission records compare attested agent/image digests with allowlists.
- Every terminal job requires a signed cleanup receipt with zero recovered
  canaries; absent or failed receipts alert and quarantine within 60 seconds.
- Synthetic audits plant unique markers in scratch, memory, and artifacts, then
  attempt recovery from the next fresh environment.
- Object storage logs alert on access after URL expiry, cross-key access, and
  missing lifecycle deletion.
- Egress-denial counters alert on repeated DNS, RFC1918/link-local, metadata,
  SMTP, or undeclared destination attempts.
- Logs and traces are scanned for seeded secrets and customer-content canaries.

### Residual risk

- A malicious provider with host, firmware, driver, or physical access can copy
  plaintext while a normal consumer GPU computes it.
- Compromised platform KMS/control-plane authority can release keys or schedule
  data to an attacker-controlled node.
- Storage, RAM, VRAM, SSD firmware, crash dumps, hibernation files, and device
  firmware may retain data outside guest-visible cleanup.
- Signed cleanup evidence proves what the measurement component observed; it is
  not proof against a compromised signer. Hardware attestation and independent
  audits reduce, but do not eliminate, that trust.

## T-04 — malicious workload escapes the sandbox

### Attack tree

Goal: control or harm a provider machine or its network.

1. Submit a crafted input to an allowed worker image.
   1. Exploit a Blender parser, codec, Python path, add-on, driver, or GPU stack.
   2. Trigger path traversal, symlink/hardlink confusion, or special-device I/O.
   3. Exhaust CPU, RAM, VRAM, disk, process handles, or wall-clock time.
2. Cross the execution boundary.
   1. Exploit the guest kernel/hypervisor or GPU paravirtualization/passthrough.
   2. Abuse a host mount, privileged device, management channel, clipboard,
      shared directory, socket, or inherited credential.
   3. Reach the host/LAN through unrestricted network or virtual-switch flaws.
3. Persist or move laterally.
   1. Write host startup locations or modify the provider agent.
   2. Steal node credentials and impersonate the provider.
   3. Scan the provider LAN, metadata services, or other local workloads.

### Controls and load-bearing control

The load-bearing control is the disposable full-VM boundary with no host mounts
or shared user session, a minimal patched guest, and a dedicated IOMMU-isolated
GPU/device assignment. Containers and process restrictions are defense in depth
for curated inference; they are not the only boundary for hostile `.blend` or
game binaries.

If the VM/hypervisor or assigned GPU boundary fails, an attacker may obtain host
kernel execution. The platform immediately disables the affected image/runtime
combination globally, quarantines involved nodes, preserves content-free
forensic evidence, rotates node credentials, and invokes the sandbox-escape
runbook.

### GPU meaning and Windows feasibility

“GPU passthrough only to the sandbox” means the host does not concurrently use
that physical GPU for its desktop or another tenant; the IOMMU maps the device
only to the guest; reset is supported at the device/function level; no host
CUDA/graphics context handles customer buffers; and the guest is destroyed
before reassignment. Consumer Windows commonly uses shared GPU virtualization
for Windows Sandbox/WSL2 rather than exclusive device assignment. That improves
convenience, but enlarges the shared host-driver attack surface and cannot meet
the isolated tier by itself. A provider without compatible virtualization,
IOMMU isolation, a spare/dedicated GPU, and supported reset remains in a lower
tier.

### Detection

- VM lifecycle and virtual-switch policy events are reconciled with one job and
  one receipt; orphan VMs or devices quarantine the node.
- Host integrity monitoring watches the agent binary, service configuration,
  boot/startup entries, hypervisor policy, and unexpected child processes.
- Denied syscalls/device access and egress are aggregated by image digest and
  reason, never job/customer content.
- Canary jobs attempt host-path, LAN, metadata, credential, and cross-tenant
  access; any success is SEV-0.
- Runtime/image CVEs are continuously inventoried from signed SBOMs with a
  48-hour critical remediation SLA.

### Residual risk

- Hypervisor, guest kernel, CPU, IOMMU, firmware, and GPU-driver escapes remain
  possible, including unknown vulnerabilities.
- Resource caps preserve host availability only within limits supported by the
  hypervisor/device; some GPU hangs require host reboot.
- A compromised provider host can falsify software-only telemetry.
- No sandbox protects a provider who disables virtualization/security features
  or installs an unsigned agent; such a node must not be admitted.

## Security decision

Do not open third-party render or cloud-gaming supply on the present bare-host
runtime. An internal owner-controlled pilot may continue with synthetic or
owner-supplied files, clearly labeled as unsandboxed. External isolated supply
requires all exit gates in `docs/security/render-sandbox-design.md` and the
external assessment in `docs/security/external-penetration-test-scope.md`.
