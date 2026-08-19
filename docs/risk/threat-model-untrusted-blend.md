# Threat model: untrusted Blender `.blend` input

**Owner:** R4 Security & Sandbox Engineer

**Decision:** `--disable-autoexec` is defense in depth, not a security boundary.

## Current exposure

The current agent launches Blender on the provider OS. It uses a temporary work
directory and passes `--disable-autoexec`, but the provider process, filesystem,
network, GPU driver, and local network remain reachable according to the host
user's permissions. Graceful cleanup does not cover power loss, forced process
termination, hibernation, filesystem snapshots, swap, or VRAM. The
`render_eligible` database flag limits who receives work; it does not contain it.

Third-party `.blend` files therefore remain prohibited on third-party nodes.

## Abuse cases and required controls

| Abuse case | Attacker action | Required prevention | Required detection |
|---|---|---|---|
| Embedded execution | Embed Python, handlers, drivers, add-ons, expressions, malformed data, or exploit a parser/codec | Curated minimal Blender image; `--disable-autoexec`; no add-ons; full VM; non-admin guest; patched Blender/runtime | Child-process and integrity events; canary scenes; crash/denial-rate alerts |
| Path traversal | Set absolute/relative output paths, use symlinks, device paths, UNC paths, or filename expansion | Ignore scene output; runtime generates an opaque output name under a mounted per-job scratch volume; open safely without following links; upload only that exact file | Receipt records bounds/result class only; reject unexpected filesystem mutations |
| Resource exhaustion | Create extreme geometry, textures, samples, frames, recursion, memory pressure, fork bombs, or GPU hangs | One frame per VM; CPU/RAM/VRAM/scratch/process/handle ceilings; wall deadline; output byte cap; kill whole VM | Limit-reason metrics; host pressure alert; watchdog independent of guest |
| Network exfiltration/lateral movement | Reach Internet, DNS, provider LAN, router, localhost services, link-local/metadata, SMB, SMTP, C2 | Hypervisor virtual switch default-deny; allow only one short-lived source GET and output PUT endpoint or use a platform fetch/upload proxy; block RFC1918, loopback, link-local, multicast, and all other DNS | Denied-flow counts by destination class; any successful undeclared flow is SEV-0 |
| Oversized artifacts | Fill scratch or upload unbounded output | Preallocated sparse/encrypted scratch ceiling; upload content-length ceiling; single-object key; abort and destroy VM at limit | `artifact_limit_exceeded` counter; storage size/lifecycle reconciliation |
| Host escape | Exploit guest kernel, hypervisor, GPU stack, integration services, or mounted host data | Full VM; minimal integration services; no clipboard/shared folders/host mounts; IOMMU-isolated dedicated GPU; signed image; current patches | Host integrity monitor; attestation drift; escape canaries; independent penetration test |
| Persistence after job | Survive in temp files, VM disk, logs, RAM/VRAM, hibernation, crash dumps, or agent cache | Unique encrypted volume/key; no persistent worker cache containing customer data; VM power-off/destroy; key destroy; GPU reset/scrub; startup orphan reconciliation | Signed cleanup receipt; marker recovery scan; missing receipt quarantines node |

## What `--disable-autoexec` covers

The flag suppresses Blender's normal automatic execution of trusted-file Python
scripts and is worth retaining. It does not turn a complex native parser and
renderer into data-only code. It cannot prevent vulnerabilities in Blender,
libraries, codecs, drivers, GPU firmware, or the operating system, and it is not
a resource, filesystem, or network boundary. Future Blender behavior and scene
features also require regression testing. Treat it as a speed bump inside the
VM, never as the reason a host is safe.

## Input and output contract

- Accept a single object with an explicit byte ceiling and verified digest.
- Never use a customer filename on the provider. Use opaque job aliases only.
- Do not expose general storage credentials or bucket listing. A presigned URL
  is scoped to one object, one method, and less than the remaining lease time.
- Copy the source into a new encrypted scratch volume; mount no provider path.
- Render exactly the claimed frame and override output format/path from policy.
- Upload exactly one bounded object, then revoke/expire access.
- Destroy the VM, per-job key, volume, network policy, and GPU assignment.
- Attempt marker recovery and sign a content-free cleanup receipt.

## Fuzz and adversarial corpus

The pre-release corpus must include embedded scripts and handlers; external,
UNC, device, traversal, Unicode-confusable and very long paths; symlinks created
inside the guest; decompression bombs; oversized textures/geometry; extreme
frame/sample counts; malformed files; deliberate hangs; renderer crashes;
fork/process-tree attempts; DNS/HTTP/SMTP/SMB/RFC1918/link-local probes; GPU OOM
and reset failures; sleep/reboot/power-loss interruption; and maximum-size output.

Success means the host remains unchanged and responsive, undeclared network
flows never succeed, limits terminate the entire VM, no marker is recoverable,
and a failed cleanup blocks every subsequent claim.

## Residual risk

Full virtualization reduces but does not eliminate escape risk. GPU passthrough
adds a large driver/firmware/device surface. A malicious provider can inspect
plaintext in use. SSD, RAM, and VRAM erasure cannot be perfectly proven from
software on an already compromised host. These limits require explicit provider
and customer disclosure plus external assessment; they cannot be converted into
an “absolutely safe” product claim.
