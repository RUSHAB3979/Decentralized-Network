# Unified GPU Marketplace Plan

**Status:** Master product and engineering direction

**Created:** 2026-08-08

**Repository baseline:** TypeScript orchestrator, provider agent, shared contracts, and JavaScript web client

**Companion documents:** [PLAN.md](PLAN.md), [ARCHITECTURE.md](ARCHITECTURE.md), [SAFE-EXECUTION-PLAN.md](SAFE-EXECUTION-PLAN.md), [RISK-REGISTER.md](RISK-REGISTER.md)

## 1. Executive decision

Build a decentralized GPU marketplace rather than a cloud-gaming-only service. Independent providers contribute GPU capacity; customers consume it through purpose-built products instead of dealing directly with untrusted machines.

The platform will expose three execution primitives:

1. **Batch jobs** — finite workloads such as Blender rendering, VFX, video processing, fine-tuning, and approved custom containers.
2. **Deployments** — long-running services such as open-source model inference endpoints.
3. **Interactive sessions** — remote GPU workstations for creative applications and, later, permissioned cloud gaming.

These primitives share provider identity, scheduling, isolation, metering, billing, storage, auditing, and payout infrastructure. They have separate lifecycle and data-plane requirements and must not be forced through one generic job abstraction.

## 2. Product thesis

### Customer promise

One marketplace lets a customer:

- upload a Blender, VFX, or video workload and receive completed artifacts;
- call hosted open-source models through an OpenAI-compatible API;
- reserve an interactive GPU workstation;
- run an approved GPU container when the platform is ready for general workloads.

### Provider promise

A provider can:

- register and verify a GPU machine;
- choose supported workload categories and availability;
- cache approved models and runtime images;
- set a price floor within marketplace rules;
- receive usage-based payouts backed by auditable metering;
- keep customer workloads isolated from the provider's personal environment.

### Platform promise

The platform owns:

- customer and provider identity;
- API-key issuance and revocation;
- workload admission and scheduling;
- usage metering and customer limits;
- provider health checks and failover;
- billing records, commissions, and payout calculations;
- signed runtime images and workload policies;
- trust tiers, incident response, and audit evidence.

A provider must never issue customer API keys. Customers authenticate only to the marketplace. Providers receive short-lived workload identities and never receive a customer's permanent marketplace credential.

## 3. Product surfaces

### 3.1 Render and media jobs

Initial supported workflows:

- Blender Cycles/Eevee still-image rendering;
- Blender animation frame rendering;
- FFmpeg encoding and transcoding;
- approved AI upscaling, denoising, and frame-interpolation pipelines;
- selected VFX rendering and simulation workloads after dependency handling is proven.

Customer flow:

1. Create a project and upload source assets.
2. Select an approved application/runtime version and workload preset.
3. Select resource requirements, deadline, region preference, and spending limit.
4. Receive a price and completion-time estimate.
5. Submit the job.
6. Observe upload, queue, execution, frame/task, and artifact progress.
7. Download output artifacts and logs.

Blender is the recommended first wedge because it supports headless execution, is open source, and animation frames can be retried or distributed independently. A `.blend` file remains untrusted input because it may contain scripts; it must execute only inside a disposable sandbox with default-deny networking.

### 3.2 Hosted open-source model APIs

Two deployment modes are planned:

- **Provider-offered deployment:** a provider chooses an approved model from the marketplace catalog and keeps it warm.
- **Customer-requested deployment:** a customer requests a model/region/capacity target and the scheduler provisions it on a matching provider.

Customer API flow:

1. Customer creates a marketplace API key.
2. Customer calls an OpenAI-compatible endpoint.
3. The API gateway authenticates the key and checks balance, quota, and policy.
4. The model router selects a healthy deployment.
5. The gateway forwards the request using short-lived provider authentication.
6. Usage is independently metered and recorded.
7. The response is returned to the customer.

The initial catalog should be small: one chat model, one code model, and one embedding model with pinned revisions and reviewed commercial terms. The first runtime should expose an OpenAI-compatible API and provide measurable token, latency, and health signals.

### 3.3 Interactive GPU workstations

Interactive workstations support Blender, Unreal Engine, video editing, CAD, and other GPU desktop applications. They require a separate low-latency streaming data plane.

Session flow:

1. Customer requests a workstation profile and duration.
2. Scheduler selects a nearby provider with a compatible dedicated GPU.
3. Provider starts an ephemeral VM or trusted workstation image.
4. Customer storage is attached through a controlled project mount.
5. Video, audio, and input are streamed through an encrypted session.
6. Project changes and exports are saved to customer storage.
7. Session credentials are revoked, storage is detached, GPU memory is reset, and the workspace is destroyed.

Proprietary application licenses are BYOL unless a vendor agreement explicitly permits another model. Batch export/transcode is a different product from interactive timeline editing and should ship earlier.

### 3.4 Cloud gaming

Cloud gaming remains an interactive workload category, not the platform's only identity. It keeps its existing permission, BYOL, credential, anti-cheat, latency, and title-compatibility gates. The shared marketplace infrastructure should be built first through safer compute workloads.

### 3.5 Raw/custom GPU compute

Arbitrary customer containers are not a launch feature. Start with signed, curated runtime images and parameterized workloads. General containers are unlocked only after image scanning, strong sandboxing, egress enforcement, customer risk scoring, and incident response are production-proven.

## 4. Target users and jobs to be done

| User | Primary job | First product |
|---|---|---|
| Independent 3D artist | Render an animation faster without buying a GPU | Blender batch rendering |
| Small creative studio | Burst rendering or encoding for a deadline | Render/media jobs |
| AI application developer | Call an affordable open model through one API | Managed inference |
| AI researcher/student | Run bounded GPU experiments or fine-tuning | Curated batch compute |
| Creator with a weak laptop | Use a powerful remote creative desktop | Interactive workstation |
| GPU owner/studio/miner | Earn from idle capacity with controlled risk | Provider marketplace |

## 5. Architecture

### 5.1 Control plane

The control plane contains:

- Identity and access service for customers, providers, and administrators;
- API gateway for customer API keys, quotas, and rate limits;
- provider registry and trust-tier service;
- scheduler and capacity reservation service;
- batch job manager;
- model deployment manager and inference router;
- interactive session manager and signaling service;
- object-storage metadata and signed-transfer service;
- metering, ledger, billing, refunds, and payout services;
- append-only security and business audit events;
- PostgreSQL for durable state and a queue for asynchronous coordination.

### 5.2 Provider plane

The provider agent is responsible for:

- enrollment and cryptographic node identity;
- hardware discovery and benchmark verification;
- signed heartbeats and telemetry;
- pulling only approved, signed runtime images;
- creating isolated workload environments;
- enforcing assigned CPU, RAM, GPU, disk, network, and timeout limits;
- reporting lifecycle events and usage evidence;
- uploading logs and artifacts through scoped signed URLs;
- cleanup, GPU reset, scratch destruction, and post-job verification;
- interactive stream-host supervision where enabled.

### 5.3 Data planes

Do not route every workload identically:

- **Batch data plane:** object storage to provider sandbox to object storage.
- **Inference data plane:** customer to marketplace gateway/router to provider model endpoint.
- **Interactive data plane:** customer to provider stream directly where possible, with authenticated relay fallback; the control plane handles allocation and signaling.

## 6. Core domain model

### Provider node

Add or evolve fields for:

- provider and node identity;
- trust tier and verification state;
- GPU model, architecture, count, VRAM, and available VRAM;
- driver/runtime compatibility;
- CPU, RAM, disk, bandwidth, region, and measured latency;
- supported workload classes;
- cached runtime/model/artifact identifiers;
- current reservations and available slots;
- reliability, benchmark, incident, and price signals;
- signed agent/image version and attestation evidence.

### Batch job

A batch job includes:

- customer/project identity;
- approved workload template and pinned runtime version;
- input manifest and immutable object references;
- parameters, frame/task range, and output specification;
- resource constraints and region preference;
- quote, hard spending limit, and timeout;
- assignment, lease, attempt, progress, and artifact records;
- terminal status and independently calculated usage.

State machine:

```text
created -> uploading -> queued -> leased -> provisioning -> running
        -> uploading_output -> completed
        -> retry_wait -> queued
        -> failed | cancelled | expired
```

### Model deployment

A model deployment includes:

- model ID, pinned revision, license metadata, and runtime image;
- quantization, context length, and minimum resources;
- provider assignment, endpoint identity, and health status;
- warm/cold mode, capacity, concurrency, and price policy;
- observed latency, throughput, error rate, and last health check.

State machine:

```text
requested -> scheduled -> downloading -> loading -> ready
          -> degraded -> ready
          -> draining -> stopped
          -> failed
```

### Interactive session

An interactive session includes:

- customer, node, image/profile, and application category;
- reservation window and price cap;
- signaling/relay metadata with short lifetimes;
- measured latency, stream quality, and disconnect events;
- project-storage attachment and teardown evidence.

## 7. API evolution

Preserve the current APIs while evolving them behind authenticated contracts.

### Provider and capacity

```text
POST /v1/providers/enroll
POST /v1/providers/heartbeat
POST /v1/providers/offers
GET  /v1/capacity
```

### Batch jobs and artifacts

```text
POST /v1/projects
POST /v1/projects/:id/uploads
POST /v1/quotes
POST /v1/jobs
GET  /v1/jobs/:id
POST /v1/jobs/:id/cancel
GET  /v1/jobs/:id/artifacts
```

### Models and inference

```text
GET    /v1/models
POST   /v1/deployments
GET    /v1/deployments/:id
DELETE /v1/deployments/:id
POST   /v1/api-keys
GET    /v1/api-keys
DELETE /v1/api-keys/:id
POST   /v1/chat/completions
POST   /v1/embeddings
```

### Interactive sessions

```text
POST /v1/workstations/quotes
POST /v1/sessions
GET  /v1/sessions/:id
POST /v1/sessions/:id/end
WS   /v1/sessions/:id/signaling
```

## 8. Scheduling

### Hard filters

A provider is ineligible when any required condition fails:

- fresh heartbeat and schedulable state;
- workload class enabled by the provider;
- sufficient CPU, RAM, VRAM, disk, and GPU compatibility;
- required runtime/image/model compatibility;
- customer/provider region or policy constraints;
- trust tier required by the workload;
- price within the customer's hard limit;
- no quarantine, unresolved incident, or capacity conflict.

### Ranking signals

Rank remaining candidates using workload-specific weights:

- expected completion time or tokens per second;
- verified price/performance;
- model/runtime cache warmth;
- historical success and retry rates;
- current utilization and queue depth;
- measured network quality and region;
- provider reliability and recent health;
- artifact transfer cost.

For batch jobs, lease assignment rather than marking a job running immediately. A provider must acknowledge the lease; lease expiry returns the work to the queue. For animations, schedule frame chunks that can be retried independently while avoiding excessive repeated asset transfer.

## 9. Storage and artifact handling

- Store source projects and final outputs in platform-controlled object storage.
- Give providers short-lived, job-scoped signed URLs.
- Encrypt objects at rest and in transit.
- Use immutable input manifests with hashes.
- Never expose storage master credentials to a provider.
- Separate source, scratch, logs, and output retention policies.
- Allow customer-controlled deletion and automatically expire temporary artifacts.
- Require packed Blender dependencies or validate and report missing external assets before billing execution.
- Validate expected frame/task outputs before declaring completion.

Encryption cannot stop a malicious provider with host control from observing plaintext while an ordinary GPU processes it. Community-provider privacy limitations must be disclosed. Sensitive workloads should require verified/dedicated providers and, where technically supported and independently verified, stronger confidential-compute tiers.

## 10. Metering, pricing, and payouts

### Billable units

- Batch compute: reserved GPU-seconds plus optional CPU, storage, and egress.
- Render workflow: GPU-seconds with a pre-job estimate; per-frame display may be used for customer clarity.
- Managed inference: input/output tokens or request units, reconciled with GPU runtime.
- Interactive session: reserved GPU minutes plus relay/egress where applicable.

### Ledger rules

- Every charge and provider earning is an immutable ledger entry.
- Quotes include an expiry and a hard maximum.
- A workload stops or requires approval before exceeding its cap.
- Metering is calculated or corroborated by the control plane; provider self-report alone is insufficient.
- Failed work is not billable except for clearly disclosed, bounded cases.
- Automatic credits cover platform-attributable failures.
- Provider payout is released only after the dispute/verification window.

Do not build an unregulated stored-value wallet without payment and legal review. Use a licensed payment provider and keep the internal ledger as accounting evidence rather than pretending to be a bank.

## 11. Security and trust requirements

### Launch controls

- AuthN/AuthZ for every non-public route;
- hashed customer API keys with prefix-based lookup and revocation;
- short-lived provider credentials and mTLS;
- signed provider agent and runtime images;
- no privileged containers, host mounts, Docker socket, or provider secrets in jobs;
- disposable per-job/session storage;
- default-deny egress for curated workloads;
- CPU/RAM/VRAM/disk/time/output limits;
- malware and policy checks on inputs where practical;
- append-only lifecycle, access, billing, and administrative audit events;
- provider KYC, agreement, payout verification, and trust tiers;
- incident quarantine, key rotation, and kill-switch procedures.

### Workload-specific controls

- Blender: disable auto-execution where possible, then still sandbox as if scripts execute.
- Video/media: protect against malformed media parsers with patched minimal images and limits.
- AI inference: keep customer API keys at the gateway; isolate deployments; disclose prompt privacy limitations.
- Interactive workstations: ephemeral credentials, encrypted streaming, controlled storage mounts, verified teardown.
- Proprietary applications/content: BYOL or written commercial permission; never redistribute provider-owned licenses.

## 12. Delivery roadmap

Progress is gate-based. Do not advance because a calendar date arrived.

### Phase 0 — Align the architecture

Deliverables:

- adopt batch/deployment/interactive as explicit workload classes;
- write architecture decision records for the shared control plane and separate data planes;
- update contracts without breaking the current MVP;
- extend the risk register for model hosting, creative files, and interactive workstations.

Exit gate:

- agreed domain model, state machines, trust boundaries, and MVP scope;
- no ambiguity about who issues API keys, owns metering, or holds artifacts.

### Phase 1 — Durable and authenticated foundation

Deliverables:

- PostgreSQL repositories for providers, jobs, leases, and audit events;
- queue-backed scheduling with acknowledgements and lease expiry;
- customer/provider/admin authentication and authorization;
- cryptographic provider identity and signed heartbeats;
- object-storage upload/download flow using scoped signed URLs.

Exit gate:

- orchestrator restart does not lose state;
- unauthorized calls fail;
- orphaned leases recover deterministically;
- storage credentials never reach a provider.

### Phase 2 — Single-node Blender vertical slice

Deliverables:

- approved Blender runtime image with pinned version;
- packed project upload and validation;
- real headless render in an isolated environment;
- progress, logs, artifact upload, cancellation, timeout, and cleanup;
- GPU-time metering and a hard job spending cap.

Exit gate:

- repeated end-to-end renders produce valid artifacts;
- malicious-script and resource-exhaustion tests remain contained;
- cancellation and node failure do not leave a billed phantom job;
- provider filesystem cleanup is verified.

### Phase 3 — Multi-provider render marketplace

Deliverables:

- provider onboarding, benchmarking, pricing, and reputation;
- frame-chunk scheduling and retries;
- independently verified usage ledger;
- customer payments, refunds, provider earnings, and payout reports;
- production monitoring and incident quarantine.

Exit gate:

- real users complete paid render jobs on multiple external providers;
- success rate, estimate accuracy, gross margin, disputes, and provider earnings are measurable;
- failed frames retry without restarting the full animation.

### Phase 4 — Managed model inference

Deliverables:

- reviewed model catalog with pinned revisions and license records;
- deployment manager and provider-side model runtime;
- marketplace API-key lifecycle;
- OpenAI-compatible chat and embedding endpoints;
- health-aware routing, rate limits, quotas, usage records, and failover;
- explicit privacy tier and retention disclosures.

Exit gate:

- requests route only to healthy compatible deployments;
- revoked keys stop working promptly;
- token/usage reconciliation stays within an agreed tolerance;
- provider failures trigger safe retry/failover behavior.

### Phase 5 — Media workflows and interactive workstations

Deliverables:

- FFmpeg and selected approved media pipelines;
- checkpoint/dependency design for supported VFX jobs;
- ephemeral GPU workstation image;
- interactive streaming, storage mounting, save/teardown, and session billing;
- application-specific BYOL/permission controls.

Exit gate:

- batch media outputs are deterministic and bounded;
- interactive pilot sessions meet defined latency, reliability, persistence, and wipe criteria;
- no proprietary license is supplied or shared without permission.

### Phase 6 — Permissioned cloud gaming and broader compute

Deliverables:

- reuse the proven interactive session plane for permitted gaming;
- enforce title rights and compatibility gates;
- consider broader containers only after sandbox and egress review;
- add enterprise/dedicated capacity tiers where demand justifies them.

Exit gate:

- each enabled workload has documented rights, isolation, metering, support, and incident controls;
- no product category can bypass the shared trust and ledger systems.

## 13. Testing strategy

### Contract and unit tests

- schema compatibility and invalid input rejection;
- state-machine transition rules;
- scheduling hard filters and deterministic ranking;
- quote, cap, usage, refund, and payout arithmetic;
- API-key creation, scope, rotation, and revocation.

### Integration tests

- provider enrollment to heartbeat to assignment;
- signed upload to execution to artifact download;
- lease expiry and provider reconnect;
- deployment provision to health routing to drain;
- session allocation to teardown.

### Adversarial tests

- forged heartbeat and benchmark claims;
- expired/replayed provider credentials;
- sandbox escape attempts and forbidden network access;
- malicious Blender scripts and malformed media;
- oversized output/log attacks;
- double billing, duplicate completion, and fake usage reports;
- provider disconnects during upload, execution, and result transfer.

### Performance tests

- scheduler latency under provider/job growth;
- queue throughput and retry storms;
- large project transfer and cache effectiveness;
- model time-to-ready, time-to-first-token, throughput, and error rate;
- interactive RTT, jitter, packet loss, frame rate, and relay rate.

## 14. Success metrics

### Marketplace

- active verified providers and schedulable GPU-hours;
- paid customers, repeat rate, and time to first successful workload;
- matched demand, utilization, provider earnings, and provider churn;
- gross margin by workload class.

### Batch/render

- quote-to-start latency;
- successful jobs and frames;
- estimate error for cost and completion time;
- retries, artifact validation failures, and refund rate.

### Inference

- deployment time-to-ready;
- request success rate and time-to-first-token;
- tokens per second and cost per token;
- healthy capacity, failover rate, and key-abuse rate.

### Interactive

- time to first frame;
- session success and unexpected disconnect rate;
- measured RTT/jitter/frame rate;
- save/teardown success and cleanup verification.

### Security

- unauthorized request rejection;
- attestation and wipe failures;
- provider quarantines and abuse incidents;
- mean time to detect, contain, and resolve an incident.

## 15. MVP scope and non-goals

### MVP must include

- one real provider GPU;
- one pinned Blender runtime;
- project upload and validated output download;
- real isolated execution, cancellation, timeout, and cleanup;
- durable job and lease state;
- basic customer/provider authentication;
- measured GPU usage and a hard spending cap;
- logs sufficient to explain every lifecycle transition.

### MVP explicitly excludes

- arbitrary containers;
- anonymous providers;
- crypto mining;
- confidential-inference claims;
- automatic support for every Blender/VFX/video version or plugin;
- interactive editing and gaming in the same initial milestone;
- decentralized payments or tokens;
- multi-country launch.

## 16. Immediate execution backlog

1. Approve this document as the product-level source of direction.
2. Write ADRs for workload primitives, API-key ownership, data planes, object storage, and provider trust boundaries.
3. Extend shared contracts with workload class, provider runtime capabilities, and lease semantics.
4. Design durable provider/job/lease/audit schemas before selecting implementation details.
5. Build a threat model for uploaded Blender projects and provider-hosted execution.
6. Produce and test one pinned Blender runtime image on a controlled GPU.
7. Implement the smallest real path: upload -> queue -> lease -> render -> artifact -> cleanup.
8. Add quote, usage, cap, and refund ledger rules before accepting payment.
9. Recruit a small controlled provider and creator pilot only after isolation tests pass.
10. Begin managed inference only after the batch control plane and metering are reliable.

## 17. Standing product rules

1. One marketplace, multiple purpose-built workload experiences.
2. The marketplace issues customer API keys; providers never do.
3. Hard eligibility filters run before price/performance ranking.
4. Provider self-report is evidence, not truth; verify capabilities and usage independently.
5. Curated workloads precede arbitrary code.
6. No credential, storage master key, or platform secret enters a provider workload.
7. Every workload has a spending cap, cancellation path, deterministic cleanup, and audit trail.
8. Privacy claims must match what untrusted provider hardware can actually guarantee.
9. Proprietary software and content require customer BYOL or written commercial permission.
10. Ship Blender batch rendering first; expand only after measurable reliability and security gates pass.
