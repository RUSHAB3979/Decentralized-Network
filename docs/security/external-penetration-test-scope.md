# External penetration-test scope: provider isolation and data cleanup

**Owner:** R4 Security & Sandbox Engineer

**Gate:** required before third-party isolated render/cloud-gaming supply

**Assessor:** independent of the sandbox implementation team.

## Objectives

1. Escape from a customer workload into the provider host, supervisor,
   management network, provider LAN, device firmware or another tenant.
2. Recover customer content after normal completion, cancellation, timeout,
   crash, sleep/resume, reboot and simulated sudden power loss.
3. Exfiltrate through network, DNS, object transfers, artifacts, logs, metrics,
   receipts, crash paths or shared GPU resources.
4. Bypass admission using forged/stale posture, unsigned agent/image, replayed
   receipt, stolen node identity or race/concurrent claims.
5. Deny service or evade limits through CPU/RAM/VRAM/disk/output/process/network
   exhaustion and GPU hangs.

## In-scope components

- exact signed provider supervisor binary and updater;
- platform-specific full-VM runner and immutable Blender/inference images;
- hypervisor configuration, virtual switch/firewall and management channel;
- dedicated GPU assignment, reset/scrub and supported driver/firmware versions;
- encrypted volume/key lifecycle and cleanup receipt/attestation verification;
- provider enrollment, job admission/claim/lease/result paths and quarantine;
- presigned source/output transfer proxy or guest networking;
- security events, metrics, crash reports and artifact handling;
- recovery after interrupted lifecycle and malicious `.blend` corpus.

Cloud-gaming media/input/TURN paths enter scope before that workload launches.
Provider payment and unrelated customer UI are excluded except where they allow
security-boundary bypass.

## Required test environments

- production-equivalent Linux KVM/VFIO profile;
- each Windows Hyper-V/DDA profile proposed for eligibility;
- supported GPU vendor/family/reset class combinations;
- one negative/ineligible consumer configuration to verify fail-closed behavior;
- isolated staging control plane, storage and key authority containing only
  synthetic accounts, markers and credentials.

No customer content or production credential is used. Testing production,
denial against shared services, persistence outside assigned hosts, social
engineering, or third-party networks requires separate written authorization.

## Attack catalogue

- malicious Blender scripts/handlers/drivers/add-ons and parser/codec fuzzing;
- host/device/UNC/traversal/symlink/hardlink/special-path output attempts;
- guest-to-host integration services, sockets, clipboard, folders, RDP/SSH/USB;
- Internet/DNS/SMTP/SMB, loopback, RFC1918, link-local/metadata, IPv6, tunnels,
  rebinding, redirects and allowed-endpoint abuse;
- hypervisor/guest-kernel/device/driver escape techniques applicable to versions;
- memory/disk/VRAM/cross-job marker recovery and artifact/log covert channels;
- stolen/replayed/malformed node tokens, attestation, policy and receipts;
- job/receipt mismatch, concurrent claim, lease expiry and cleanup races;
- watchdog kill, supervisor kill, guest crash, host sleep/reboot and power loss
  at every cleanup boundary;
- resource and oversized upload/output exhaustion, GPU hang/reset failure;
- updater/signature/downgrade/image-substitution and SBOM/provenance bypass.

## Rules of engagement

The assessor receives architecture, source and exact builds (white-box), asset
inventory, permitted targets, UTC window, contacts, stop conditions and safe
test accounts. Stop immediately on escape beyond dedicated staging, risk to
people/third parties, uncontrolled propagation, non-synthetic data, or inability
to restore the host. Notify the emergency contact out of band; do not place
exploit details or secrets in normal ticketing.

Evidence uses synthetic marker IDs, UTC, component digest and minimal redacted
reproduction. Raw dumps remain encrypted with access/custody log and shortest
agreed retention.

## Severity and exit criteria

- **Critical:** host/other-tenant escape, undeclared network access with code
  execution/exfiltration, admission of unsigned boundary, cleanup bypass followed
  by data recovery, or compromise of platform signing/key authority.
- **High:** reliable customer-content recovery, provider credential theft,
  quarantine bypass, persistent host modification, or resource attack requiring
  manual host recovery.
- **Medium/low:** constrained weakness with no boundary crossing, hardening or
  defense-in-depth gap.

No critical/high isolation finding may remain open. Each is remediated in a new
signed build, regression-tested and retested by the assessor. Medium findings
need accepted owner/date/compensating control. The final deliverables are an
executive report, technical report, attack-path map, evidence list, retest
letter and content-free public summary. R4 issues the evidence pack; R1 records
the separate business/architecture decision to open third-party supply.
