# Render sandbox design and provider eligibility

**Owner:** R4 Security & Sandbox Engineer

**Decision date:** 2026-08-20

**Decision:** use a disposable full VM with an exclusively assigned GPU for
third-party render jobs. Consumer Windows process/container/WSL2 paths do not
qualify as the sole hostile-input boundary.

## Platform comparison

| Option | GPU path | Isolation finding | Provider cost | Decision |
|---|---|---|---|---|
| Windows Sandbox | Shared vGPU; Microsoft warns vGPU increases attack surface | Separate kernel, but shared host GPU stack, limited lifecycle orchestration, no Home support | Low setup on supported Pro/Education/Enterprise editions | Defense-in-depth test environment; not isolated tier |
| WSL2/container | GPU is projected from the Windows host driver into WSL; known CUDA feature/telemetry limits remain | Shares the Windows GPU/virtualization path and is not exclusive device assignment | Docker/WSL/driver setup and reboot; attractive for curated inference | Vetted inference only after validation; not hostile render boundary |
| Hyper-V full VM with DDA | Whole PCIe device assigned to a guest | Strongest Windows option when IOMMU/ACS/device/vendor support exists | Requires Hyper-V-capable edition/host, compatible hardware, spare GPU, admin setup | Isolated tier only on an explicitly certified configuration |
| Linux KVM/QEMU with VFIO | Whole IOMMU group assigned to a guest | Mature full-VM boundary; still exposed to hypervisor/GPU/firmware escapes | Linux host expertise, IOMMU-safe topology, dedicated GPU | Preferred isolated provider profile |
| gVisor/Kata/Firecracker without exclusive GPU assignment | Efficient for CPU workloads; GPU integration varies and may reintroduce host driver sharing | Useful reduced attack surface, but not by itself an approved GPU boundary | Lower steady-state overhead, higher integration work | Candidate for curated CPU/inference; separate GPU security review required |

Microsoft currently documents that Windows Sandbox is unavailable on Windows
Home, has shared vGPU support, and enables networking by default; its own
configuration guidance notes that vGPU increases attack surface. Microsoft's
documented DDA deployment path applies to Windows Server and requires compatible
IOMMU/ACS hardware and a vendor-supported device. Hyper-V client itself requires
Windows Pro or Enterprise. NVIDIA documents that WSL2 uses the Windows host GPU
driver projection and retains feature limitations. Sources:

- [Microsoft: Windows Sandbox editions and behavior](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/)
- [Microsoft: Windows Sandbox configuration and vGPU warning](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-configure-using-wsb-file)
- [Microsoft: Hyper-V and DDA hardware requirements](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/host-hardware-requirements)
- [Microsoft: graphics-device DDA deployment scope](https://learn.microsoft.com/en-us/windows-server/virtualization/hyper-v/deploy/deploying-graphics-devices-using-dda)
- [NVIDIA: CUDA on WSL constraints](https://docs.nvidia.com/cuda/archive/13.0.2/wsl-user-guide/index.html)

The founder's Windows 11 Home machine cannot use Windows Sandbox or the
supported Hyper-V client feature set described above. It may run the
owner-controlled pilot, but it cannot prove the production isolated tier.

## Honest capacity finding

The project cannot claim a percentage of consumer gaming PCs that qualify
without measuring enrolled hardware. The isolated requirements exclude Windows
Home, single-GPU machines whose desktop needs that GPU, systems without exposed
IOMMU/ACS isolation, unsupported consumer device passthrough, and devices that
cannot reset reliably. That is plausibly a minority of the intended consumer
supply, but the percentage is unknown.

Enrollment must run a signed, content-free capability probe and publish counts
by coarse failure reason. Product planning uses measured eligible capacity, not
total registered GPUs. If supply is insufficient, use platform-controlled Linux
hosts or vetted professional providers rather than weakening the boundary.

## Runtime architecture

```text
signed host supervisor (no customer data)
  -> verify node posture, image digest, policy and job alias
  -> create virtual switch with no route
  -> create unique encrypted scratch volume and platform-held DEK
  -> boot immutable minimal VM
  -> exclusively attach reset-capable GPU
  -> fetch one source object through constrained transfer channel
  -> run one Blender frame with hard resource/deadline ceilings
  -> upload one bounded output object through constrained channel
  -> power off VM and terminate its process tree
  -> detach/reset/scrub GPU; destroy VM, DEK, volume and network policy
  -> scan for synthetic markers; sign content-free cleanup receipt
  -> permit next claim, or quarantine on any failed/unknown step
```

The supervisor stores policy state and receipts outside the disposable guest,
but never customer content. The platform-specific runner must implement the
same admission and terminal contract as `security/runtime_contract.py`.

### Immutable guest

- Secure/verified boot where supported; production image identified by signed
  SHA-256 digest and matched to an SBOM.
- Minimal OS, Blender build, renderer, transfer helper, watchdog, and receipt
  measurement component. No package manager, browser, shell service, SSH, RDP,
  add-ons, compilers, or general storage SDK.
- Read-only base image. One encrypted scratch volume and no host mounts, shared
  folders, clipboard, microphone, camera, USB, printer, or enhanced session.
- Non-administrative Blender account. Disable auto-execution and override scene
  output path/format/frame from the signed policy.
- One VM and one assigned physical GPU per active tenant job.

### Network

Default state is no route and no DNS. Preferred transfer design is a narrow
host-side proxy that understands only one expected object GET and one output
PUT, enforces byte limits, pins the resolved address/TLS name, strips ambient
credentials, and expires before the lease. If direct guest transfer is used,
the virtual switch/firewall allowlist must provide equivalent method, endpoint,
address, time, and byte bounds.

Always deny loopback-to-host, RFC1918/provider LAN, link-local and cloud metadata,
multicast, inbound connections, SMTP, SMB, arbitrary DNS, and any endpoint not
declared in policy. Do not log presigned URLs.

### Resources and watchdog

The signed policy sets CPU cores, RAM, VRAM, scratch bytes, output bytes,
process/handle count, and wall-clock deadline. A watchdog outside the guest
terminates the entire VM, not just Blender. Host pressure thresholds stop new
claims before the provider becomes unusable. A GPU that hangs or fails reset is
removed from service; it is never reassigned on a best-effort result.

### Sleep, reboot, crash, and orphan handling

- Disable new claims while the host is preparing to sleep or shut down.
- Treat suspend longer than the lease as interruption; never silently resume a
  customer computation under a new lease.
- Persist only opaque lifecycle state needed to find the VM/volume/device after
  restart. Do not persist URLs, filenames, prompts, or output content.
- Before the first post-startup heartbeat can advertise availability, enumerate
  orphan VMs, volumes, virtual switches, keys, processes, and GPU assignments.
- Destroy and verify every orphan. Any uncertainty quarantines the node until a
  privileged operator audit; no automatic quarantine clearance exists.

## Cleanup proof

A valid cleanup receipt proves that the observed process tree stopped, the
ephemeral key and volume were destroyed, temporary paths and network policy were
removed, GPU cleanup/reset was verified, orphan reconciliation passed, and no
canary was recovered. It contains only opaque aliases, image/workload identity,
timestamps, booleans/counts, and signer key ID. It is signed by a hardware-backed
node/measurement identity and verified centrally.

Deleting files is not the proof. Cryptographic erasure of a unique per-job key
is the primary retained-storage control. GPU reset/scrub capability must be
vendor/device specific: when reliable reset cannot be demonstrated, the device
does not qualify. A software signature from the same compromised host is only
tamper evidence; remote attestation plus independent audits remain necessary.

## Eligibility and exit gates

A third-party node may be marked render-eligible only when all are true:

- authenticated provider enrollment and revocable node identity;
- compatible hardware/edition, virtualization, IOMMU group and GPU reset probe;
- full-VM runner integrated with the security admission state machine;
- signed supervisor and immutable allowlisted image with current SBOM;
- deny-by-default egress test suite passes;
- hard resource, deadline, source, scratch, and output bounds pass;
- normal, cancel, timeout, Blender crash, agent crash, sleep/resume, reboot, and
  simulated power-loss tests each produce either valid cleanup or quarantine;
- marker recovery is zero across scratch, subsequent guest, logs, RAM/VRAM tests
  supported by the device, and object transfer paths;
- cleanup failure prevents the next claim and pages within 60 seconds;
- current critical CVEs are remediated within the 48-hour policy;
- external penetration test completes with no open critical/high isolation
  finding and all agreed retests pass;
- an R1 architecture record authorizes opening supply based on measured eligible
  capacity and the R4 evidence pack.

Until then, `render_eligible` remains false for every machine not controlled by
the project owner. This design does not authorize changing that column.

## Cloud-gaming extension

Interactive gaming adds continuous media/input channels. Its isolated compute
boundary remains the same. Privacy mode must force relay-only ICE/TURN so the
customer and provider never learn each other's IP address; direct peer-to-peer
candidates are not gathered or exchanged. TURN credentials are per-session,
short-lived, and absent from logs. Direct mode, if ever offered, requires a
separate explicit privacy disclosure and threat review.
