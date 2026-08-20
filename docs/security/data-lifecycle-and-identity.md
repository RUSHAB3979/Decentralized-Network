# Customer-data lifecycle and private node identity

## Data classification

| Class | Examples | Provider handling | Telemetry handling |
|---|---|---|---|
| Customer content | prompts, responses, `.blend`, frames, model weights, game saves/input/audio/video | only inside authorized job boundary; terminal deletion | prohibited |
| Job capability | presigned object operation, encrypted envelope, per-job DEK grant | one job/method/object; expires before lease | outcome only; never value |
| Private identity | user ID, provider enrollment ID, node credential, customer/provider IP | control plane only; not sent cross-party | access-controlled security audit only |
| Public alias | rotating job/session/provider display alias | minimum needed | permitted with retention bounds |
| Security evidence | digests, tier, bounded reason codes, content-free receipt | supervisor/control plane | permitted; no customer content |

## Lifecycle

1. Accept the minimum content needed for one job. Validate type, digest and byte
   ceiling before scheduling.
2. Generate an opaque job alias unrelated to customer/provider/hardware identity.
3. Envelope-encrypt queued content with a unique job DEK. Store ciphertext and
   encryption metadata separately from the key authority.
4. Release the minimum decryption/transfer capability only after node posture
   and job admission pass. Capability lifetime is shorter than the remaining
   lease and is scoped to one operation/object.
5. Keep content only in the disposable guest and encrypted per-job scratch.
6. On every terminal state—including cancellation, timeout and failure—revoke
   capabilities, destroy the DEK, delete source/queued content under the
   platform retention policy, destroy provider scratch, and produce cleanup
   proof. Artifact retention is a separate customer-visible policy.
7. Reconcile terminal jobs against key, database, object-storage and receipt
   inventories. Any unmatched record alerts and blocks affected supply.

## Current repository gaps requiring other owners

- Inference request messages are stored as plaintext JSONB job payload and are
  not cleared at terminal state. API wording must not claim they are unstored.
- Provider enrollment can mint a node token without authenticated authorization,
  allowing a fake provider to become a candidate for customer inference.
- The provider token is stored as plaintext on disk.
- Render source/artifact object lifecycle and verified deletion are not enforced
  in this repository.
- Provider temporary render files are cleaned on graceful paths, but crash,
  reboot and power-loss residue is not covered by a startup proof/quarantine.

R4 records the required controls; R1/R2/R3/R5/R6/R9 implement them in their
owned control-plane, database, storage, agent and user-experience areas. See
`cross-team-handoffs.md`. These gaps block external customer workloads where
the corresponding data crosses an untrusted node.

## Identity and fingerprinting

A stable internal provider identity is necessary for authentication, abuse
response, payment, revocation, audit continuity and duplicate-enrollment
detection. Removing it would make the network easier to attack. It must instead
remain private and pseudonymous.

- Generate node/enrollment IDs server-side. Never expose MachineGuid, MAC,
  serial number, hostname, Windows username, install path, public IP, or raw
  hardware fingerprint to customers or other providers.
- If duplicate-device detection is required, submit measurements over an
  authenticated channel and store a versioned server-keyed HMAC, not a raw or
  plain hash. Restrict access, rotate the HMAC key/version, and document deletion.
- Use separate rotating display/job/session aliases. They must not be usable to
  join activity across customers or long time windows.
- MachineGuid-derived values do not themselves create remote-access capability,
  but they are stable correlators and must not be public or logged broadly.
- Do not send the customer's IP to the provider. Current orchestrator-mediated
  job polling preserves this property. Future WebRTC/cloud gaming privacy mode
  uses relay-only ICE/TURN and suppresses host/server-reflexive candidates.
- Credentials are random, revocable, scoped and rotated—not derived from device
  attributes. Store provider tokens in an OS credential vault or hardware-backed
  key, never a plaintext configuration file.

## Retention requirements

Exact legal/product durations require the legal and data owners. Until approved,
the safe technical defaults are: provider scratch immediately destroyed at
terminal state; per-job DEK immediately destroyed; expired transfer capability
unusable; queued prompt/source removed once no longer needed for retry; and no
customer content in observability. Render artifacts follow a separately stated
customer retention/deletion policy and must not inherit log retention.

Backups and replicas are part of deletion scope. Where immediate physical purge
is impossible, per-object encryption keys and documented maximum backup expiry
provide crypto-erasure and a bounded residual window. Deletion evidence contains
object aliases/status/times only, never names or content.
