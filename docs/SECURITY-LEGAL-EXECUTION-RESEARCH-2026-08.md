# Security, Legal, and Execution Research Review

**Research date:** 8 August 2026

**Product:** India-first decentralized GPU marketplace

**Repository reviewed:** `RUSHAB3979/Decentralized-Network` at baseline commit `0c4b819` plus the local prototype working tree

**Decision status:** Research baseline; not a production approval

> This document is engineering and product research, not legal, tax, accounting, or insurance advice. Qualified counsel and a chartered accountant must verify obligations for the actual entity, jurisdictions, contracts, payment flow, software licences, customers, providers, and workloads.

## 1. Executive conclusion

The startup is technically executable, but the current repository is a prototype rather than a production marketplace. It is not ready to accept real customer files, execute untrusted workloads, onboard independent providers, move money, expose model APIs, or stream games.

No system can honestly be guaranteed **100% secure**. No general research report can make a product **100% legal in every jurisdiction**. The achievable standard is:

- narrow and permission-based scope;
- defence in depth;
- explicit residual-risk disclosure;
- machine-enforced workload admission;
- auditable contracts, licences, state transitions, and money movement;
- monitoring and incident response;
- independent security testing;
- jurisdiction-specific legal and tax review.

The safest executable launch sequence is:

1. India-only private prototype.
2. One controlled GPU provider.
3. One pinned headless Blender runtime.
4. No sensitive data.
5. No arbitrary customer containers or commands.
6. Manual customer, provider, and workload approval.
7. No integrated money until the ledger, refunds, reconciliation, contracts, and tax treatment pass review.
8. Multiple providers only after external sandbox assessment.
9. Curated model inference only after exact model and runtime licence review.
10. Workstations and gaming only after software, driver, platform, publisher, and anti-cheat permission is documented.

## 2. Research method and evidence

The review used:

- direct inspection of the orchestrator, contracts, provider agent, context server, frontend, CI workflow, Docker Compose, and project documentation;
- local build and TypeScript checks;
- local npm dependency audits;
- the official Digital Personal Data Protection Act, 2023;
- official CERT-In cybersecurity directions;
- NVIDIA's current driver licence;
- Valve's current Steam Subscriber Agreement;
- Blender's official licence and scripting-security documentation;
- gVisor's official GPU security documentation;
- Firecracker's official architecture design;
- NIST and OWASP security guidance.

Three delegated research branches were also attempted. All timed out and returned no evidence. No conclusion in this document relies on those failed branches.

## 3. Current implementation reality

| Capability | Evidence in current repository | Readiness |
|---|---|---|
| Frontend | Functional React prototype with explicit preview/mock messaging in important product pages | Demo only |
| Orchestrator | Express/TypeScript API with in-memory providers and jobs | Prototype only |
| Authentication | No customer/provider authentication on marketplace endpoints | Launch blocker |
| Authorization | No tenant, provider, support, finance, or admin boundary | Launch blocker |
| Persistence | PostgreSQL exists in Compose configuration, but marketplace state remains in memory | Launch blocker |
| Scheduling | Basic matching/scoring only; no transactional lease protocol | Prototype only |
| Workload execution | A job record can be created, but no production worker executes it | Not implemented |
| Sandbox | Documentation describes a target; no proven GPU sandbox exists | Not implemented |
| Storage | No production signed-upload/download and retention lifecycle | Not implemented |
| Metering | No independently verified usage pipeline | Not implemented |
| Ledger | No append-only customer charge/provider earning ledger | Not implemented |
| Payments/payouts | No processor, webhook, refund, payout, or reconciliation implementation | Not implemented |
| Gaming rights | `rights_basis` is present in documents/mock UI but absent from core `matching.ts` | Not enforced |
| Model licences | Preview catalogue intentionally says licence review is required | Correctly gated |
| Automated tests | Builds/typechecks exist; no meaningful marketplace unit/integration test suite | Insufficient |

### 3.1 Documentation-to-code contradiction

Existing risk documentation states that `rights_basis` is hard-enforced in `matching.ts`. Direct code search found no such field in the core matcher. It currently exists only in context data and frontend mock catalogue data.

Therefore, gaming rights are a documented control, not an implemented control. No game may be considered schedulable until an authoritative rights database and deny-by-default admission check exist in the production control plane.

### 3.2 Database contradiction

`docker-compose.yml` provides `DATABASE_URL`, but the current orchestrator does not consume PostgreSQL. A healthy database container does not make job/provider state durable.

### 3.3 Execution contradiction

The API accepts an image reference and command, but there is no production sandbox lifecycle. Creating a job record must not be represented as executing a workload.

## 4. Launch-scope decision

### 4.1 Allowed first workload

The first external workload should be approved headless Blender rendering with all of these limits:

- one official Blender version;
- one platform-built image pinned by immutable digest;
- platform-defined command template;
- customer supplies only a `.blend` file, packed assets, and bounded parameters;
- automatic Python execution disabled;
- no custom add-ons or external executables;
- no network access;
- non-sensitive projects only;
- one physical GPU assigned to one job at a time;
- fixed input, output, scratch, process, memory, disk, GPU, and wall-time limits;
- signed object-storage transfers;
- explicit hard spending cap;
- output validation before completion;
- verified scratch cleanup;
- manual approval during private beta.

### 4.2 Blocked at launch

- arbitrary Docker/OCI images;
- user-supplied shell commands;
- SSH or remote root access;
- cryptocurrency mining;
- scanning, credential attacks, or unrestricted egress;
- health, financial, biometric, defence, or other regulated/sensitive data;
- confidential source code on community provider machines;
- model fine-tuning on uploaded private datasets;
- public self-service provider onboarding;
- stored-value wallet or marketplace escrow controlled by the startup;
- cloud gaming;
- unreviewed proprietary workstation applications;
- cross-border public launch.

## 5. Double-untrusted architecture

This marketplace has two adversarial directions:

1. A customer workload may attack the provider.
2. A provider controlling the host may inspect or tamper with the customer's workload.

A single container does not solve both directions.

### 5.1 Encryption limitation

Encryption protects objects at rest and in transit. Ordinary GPU computation ultimately consumes plaintext. A provider controlling the host can potentially inspect host memory, GPU memory, files after decryption, model prompts, render assets, interactive video/input, and execution output.

Consequences:

- Do not promise host confidentiality on community nodes.
- Do not accept sensitive data on community nodes.
- Publish an explicit community-provider privacy limitation.
- Create separate community, verified-professional, dedicated, and independently validated confidential tiers.
- Treat platform-held object encryption keys as storage protection, not proof that a malicious host cannot observe computation.

### 5.2 Attestation limitation

TPM or measured-boot evidence can prove selected measurements. It does not prove that:

- the physical owner is not recording the session;
- firmware, BMC, or DMA devices are safe;
- the machine remains uncompromised after attestation;
- teardown occurred correctly;
- provider telemetry is honest.

Attestation must be combined with KYC, contracts, signed releases, independent measurements, canary jobs, delayed payouts, reputation, quarantine, audits, and disclosure.

## 6. GPU sandbox decision

### 6.1 Plain Docker is insufficient

Do not expose an NVIDIA device to arbitrary code in an ordinary `runc` container and describe it as secure isolation.

Minimum execution restrictions include:

- no privileged mode;
- no Docker socket;
- no host PID/network/IPC namespaces;
- no host filesystem mounts;
- non-root workload UID;
- read-only root filesystem;
- all capabilities dropped;
- seccomp plus AppArmor/SELinux where available;
- bounded tmpfs/scratch;
- cgroup CPU, memory, PIDs, disk and time limits;
- egress denied outside the sandbox at the host/network layer;
- only the assigned GPU device exposed;
- immutable signed image digest;
- disposable environment per attempt.

### 6.2 gVisor

gVisor supports many CUDA, Vulkan, NVENC, and NVDEC workloads through `nvproxy`. This can materially reduce the ordinary Linux attack surface.

Its own documentation states that GPU calls still reach NVIDIA's kernel driver, that gVisor is less effective against vulnerabilities in that driver, and that it adds no extra hardware-level isolation. Driver patching and compatibility control remain mandatory.

Decision:

- Evaluate gVisor `runsc`/`nvproxy` for the curated Blender and inference tiers.
- Pin supported driver/runtime combinations.
- Run malicious-input, resource-exhaustion, egress, and cleanup tests.
- Do not use gVisor as evidence that arbitrary GPU code is completely safe.

Source: <https://gvisor.dev/docs/user_guide/gpu/>

### 6.3 Firecracker

Firecracker's documented minimal machine model exposes VirtIO network, block, and vsock devices. Its official design does not document an off-the-shelf GPU device path.

Decision:

- Firecracker may be evaluated for CPU-only helper workloads.
- It must not be listed as an already available GPU-isolation solution.
- A separately demonstrated GPU architecture would require its own review.

Source: <https://github.com/firecracker-microvm/firecracker/blob/main/docs/design.md>

### 6.4 Dedicated VM alternative

A dedicated VM with full physical GPU passthrough can provide a stronger per-tenant boundary than a shared ordinary container, but it still depends on hypervisor, IOMMU, firmware, GPU reset, and driver correctness. It is operationally more realistic on controlled Linux hosts than personal gaming PCs.

Do not conceal virtualization indicators or spoof hardware identity to defeat DRM or anti-cheat.

## 7. Blender feasibility and licence

Blender is GPL free software, and Blender's official licence page explicitly states that users are free to sell their work. This supports commercial rendering as the initial product.

Source: <https://www.blender.org/about/license/>

However, Blender's documentation warns that `.blend` files can include Python scripts and that Python does not restrict what those scripts can do. Automatic execution being disabled does not make a file safe against parser vulnerabilities or resource abuse.

Source: <https://docs.blender.org/manual/en/latest/advanced/scripting/security.html>

### Required Blender admission and verification

1. Reject archives with excessive expansion ratio, file count, depth, or size.
2. Reject custom scripts/add-ons in the first tier.
3. Disable auto-execution explicitly.
4. Reject absolute paths and dependencies outside the input workspace.
5. Pack or validate all required assets before billing execution.
6. Restrict frames, resolution, samples, memory, output size, and runtime.
7. Default-deny network egress.
8. Monitor child processes.
9. Validate output count, type, dimensions, decodability, and hashes.
10. Use random canary and duplicate spot-render jobs to detect provider fraud.
11. Keep failed input/output according to a disclosed short retention schedule.
12. Delete scratch and revoke signed URLs after completion.

## 8. NVIDIA driver licensing risk

NVIDIA's current driver licence contains two material clauses:

- Section 2.7 restricts selling, renting, sublicensing, distributing, transferring the software, or providing commercial hosting services with it except where expressly granted.
- Section 2.8 says GeForce or Titan software is licensed for use on GeForce/Titan products the user owns and is not licensed for datacenter deployment.

Source: <https://www.nvidia.com/en-us/drivers/nvidia-license/>

This does not by itself establish that every independent home-provider use is unlawful. It creates a serious unresolved classification and licensing question:

- Who deploys the driver?
- Is the provider offering commercial hosting with the software?
- Is the marketplace redistributing the driver?
- Does the deployment qualify as a datacenter deployment?
- Is a separate enterprise/service-provider licence required?

Launch gate:

- Obtain written NVIDIA/reseller clarification and Indian counsel review before commercial onboarding of GeForce/Titan providers.
- Do not redistribute consumer drivers in provider images without confirmed rights.
- Record GPU model, driver package, licence basis, and deployment class during provider admission.
- If permission is unavailable, use appropriately licensed professional/datacenter capacity or evaluate an alternative open driver stack after its own technical and legal review.

A competitor using consumer GPUs is not proof that the licensing issue is resolved.

## 9. Managed model inference

"Open model" does not automatically mean commercially hostable or redistributable.

Every exact model revision needs an authoritative record for:

- model and revision identifier;
- weight digest;
- licence text and URL;
- commercial hosted-inference permission;
- redistribution/caching permission;
- derivative and quantized-weight treatment;
- attribution obligations;
- restricted users, uses, industries, and regions;
- runtime image and runtime licence;
- review date and reviewer;
- termination/change monitoring.

The marketplace gateway—not a provider—must own customer authentication, API keys, quotas, rate limits, routing, failover, abuse controls, retention policy, usage metering, and revocation. Providers should receive only short-lived deployment identities.

First inference pilot:

- one reviewed model revision;
- one controlled provider;
- one runtime image;
- no prompt retention by default;
- no training on prompts;
- no sensitive data;
- explicit provider-visibility disclosure;
- strict request, token, concurrency, timeout, and spending limits;
- gateway and GPU-runtime usage reconciliation.

## 10. Interactive workstations

Interactive workstations require a separate product and risk model:

- operating-system remote-hosting rights;
- application licence and BYOL rights;
- GPU driver rights;
- encrypted low-latency streaming;
- ephemeral session identity;
- controlled project storage;
- reconnect and checkpoint semantics;
- teardown and credential revocation;
- session billing and dispute evidence.

Do not preload Windows, Adobe, Autodesk, CAD, Unreal plugins, or other proprietary applications because a customer owns a local licence. Each vendor's remote access, virtualization, named-user, service-provider, and geographic terms must be reviewed for the exact design.

## 11. Cloud gaming

Cloud gaming should remain blocked.

Valve's current Steam Subscriber Agreement grants personal, non-commercial use by default unless commercial use is expressly permitted. It also restricts commercial networks/content aggregation and commercial exploitation without permission.

Source: <https://store.steampowered.com/subscriber_agreement/>

A customer's ownership of a game does not automatically grant the marketplace commercial remote-streaming, caching, distribution, or hosting rights.

Every enabled title would require documented review of:

- Steam/platform terms;
- publisher EULA and written streaming permission;
- game-binary distribution/caching rights;
- commercial territory;
- DRM;
- anti-cheat and virtualization support;
- account/session flow;
- third-party launcher terms;
- Windows and GPU driver rights.

Permanent prohibitions:

- shared marketplace accounts;
- password or Steam Guard token collection;
- `ssfn` storage or injection;
- Family Sharing arbitrage;
- peer-to-peer game-binary distribution;
- hardware-ID spoofing;
- hypervisor concealment;
- DRM or anti-cheat circumvention;
- fake or assumed publisher approval.

Required admission state is `blocked` unless documentary permission exists and counsel approves the exact configuration.

## 12. India data-protection requirements

### 12.1 DPDP Act

The Digital Personal Data Protection Act, 2023 includes obligations involving:

- lawful-purpose processing;
- notice;
- consent that is free, specific, informed, unconditional and unambiguous where consent is used;
- withdrawal of consent;
- valid contracts with processors;
- appropriate technical and organisational measures;
- reasonable security safeguards;
- breach notice to the Board and affected Data Principals in the prescribed manner;
- erasure when purpose ends, subject to legally required retention;
- rights and grievance mechanisms;
- additional duties involving children.

The Act defines a child as an individual under 18. An early launch should be 18+ unless counsel approves and the product implements the child-data obligations.

The Act's Schedule allows a penalty up to ₹250 crore for failure to take reasonable security safeguards.

Primary source: <https://egazette.gov.in/WriteReadData/2023/248045.pdf>

Some existing project documents state exact 2026/2027 commencement dates for later DPDP Rules. This review did not independently verify the final Rules and every commencement notification from the primary Gazette. Counsel must verify the current commencement schedule before those dates are treated as operational fact.

### 12.2 Data roles

For customer accounts and marketplace operations, the startup is likely to determine purposes and means and therefore act as a Data Fiduciary. Providers, object storage, identity, KYC, analytics, support, and payment vendors may process personal data on its behalf or for their own regulated purposes.

Required actions:

- create a data inventory and flow diagram;
- assign controller/fiduciary and processor roles per flow;
- sign provider and vendor data-processing terms;
- publish purposes and retention periods;
- implement consent/notice evidence where applicable;
- build access, correction, erasure, withdrawal, and grievance workflows;
- prevent providers from retaining customer data;
- maintain a subprocessor list;
- minimise telemetry and log content;
- test deletion across primary stores, replicas, search indexes, and processors.

## 13. CERT-In operational duties

CERT-In's 28 April 2022 directions state that covered service providers, intermediaries, data centres, bodies corporate, and government organisations must:

- report specified cyber incidents within six hours of noticing or being informed of them;
- designate a CERT-In point of contact;
- enable logs for ICT systems;
- retain them securely for a rolling 180 days;
- maintain the required logs within India;
- provide them to CERT-In when required.

Primary source: <https://www.cert-in.org.in/PDF/CERT-In_Directions_70B_28.04.2022.pdf>

Engineering consequences:

- India-resident security-log archive;
- reliable time synchronization;
- incident classification matrix;
- on-call primary and backup owner;
- prepared reporting template;
- immutable evidence preservation;
- rehearsal of the six-hour decision/reporting clock.

Do not put customer source files, prompts, passwords, tokens, private keys, or unnecessary personal data in security logs.

## 14. Intermediary, content, and abuse controls

The Information Technology Act and Intermediary Rules may be relevant depending on the service's legal classification and activities. Safe-harbour applicability is fact-specific and must be confirmed by counsel.

Before external launch:

- publish Terms of Service, Privacy Notice, and Acceptable Use Policy;
- provide a grievance and takedown channel;
- define acknowledgment, escalation, preservation, and resolution procedures;
- timestamp every action;
- implement emergency job/account suspension;
- preserve legal-request evidence;
- prohibit malware, credential theft, unauthorized scanning, spam, illegal content, mining, sanctions evasion, and rights-infringing workloads;
- allow a workload only when technical controls can enforce its policy.

Official IT Rules source: <https://egazette.gov.in/WriteReadData/2021/225464.pdf>

## 15. Consumer protection

A paid marketplace must not show mock capacity, providers, prices, approvals, savings, availability, usage, earnings, or testimonials as production facts.

Required product controls:

- total price and maximum charge before acceptance;
- quote expiry;
- affirmative acceptance evidence;
- clear cancellation and refund policy;
- automatic credits/refunds for platform-attributable failures where practical;
- invoice and transaction records;
- support and grievance workflow;
- no asymmetric or unfair cancellation charges;
- no blanket "no refunds" representation;
- preserved job, quote, execution, and settlement evidence.

Current preview labels should remain until the associated authoritative backend exists.

## 16. Payments, ledger, tax, and payouts

### 16.1 Payment boundary

Do not build a startup-controlled stored-value wallet or informal escrow.

Use a regulated payment provider for collection, tokenized payment methods, refunds, fraud tooling, and marketplace/split payouts where the provider contract supports the actual model.

The internal ledger must be accounting evidence, not transferable stored value.

### 16.2 Ledger design

- Append-only entries; corrections use compensating entries.
- Separate customer charge, platform fee, provider earning, tax, refund, chargeback, and payout entries.
- Quote reservation before execution.
- Hard cap enforced by the control plane.
- Provider self-report is never the only metering source.
- Signed and idempotent payment webhooks.
- Daily payment-provider reconciliation.
- Payout delay through a defined dispute/verification window.
- Payout-account change cooldown and reverification.
- No destructive edits to settled records.

### 16.3 India tax gate

Existing documents assume GST and Income-tax Act section 194-O obligations. Exact applicability, rate, threshold, place of supply, invoice flow, export-of-service treatment, and provider classification depend on the final legal/payment structure.

Before the first payout, a chartered accountant must approve:

- GST registration position;
- platform versus principal-service characterization;
- commission and provider invoicing;
- place of supply;
- TDS applicability and implementation;
- PAN and provider tax records;
- reconciliation and return calendar;
- foreign customer/provider treatment.

Do not hard-code tax rules from a planning document.

## 17. Provider agreement and onboarding

Every provider must be a verified counterparty rather than an anonymous peer.

Minimum onboarding evidence:

- verified legal identity;
- verified bank account;
- signed provider agreement;
- hardware and driver inventory;
- node certificate;
- signed agent version;
- security-baseline attestation;
- supported workload opt-ins;
- independently measured benchmark;
- tax information;
- incident contact;
- pricing and payout acceptance.

Provider agreement subjects:

- authority to use hardware, premises, power, and internet;
- confidentiality and prohibition on viewing/copying workload data;
- security baseline and update obligations;
- incident and legal-request cooperation;
- data deletion;
- audit rights;
- pricing, metering, disputes, taxes, and payouts;
- fraud and telemetry tampering;
- suspension, quarantine, termination, and appeal;
- genuine independent-business terms reflected in actual operations.

## 18. Security architecture requirements

### Identity and access

- Managed or thoroughly reviewed identity provider.
- MFA/passkeys for administrators and providers.
- Short-lived sessions and revocation.
- Hashed API keys with prefix lookup.
- Explicit customer/provider/support/finance/admin roles.
- Tenant scope on every query.
- Deny by default.
- Privileged-access audit.

### Provider identity

- Outbound-only provider control connection where possible.
- Per-node mTLS certificate.
- Certificate rotation and revocation.
- Enrollment approval separate from scheduling approval.
- Signed update manifests.
- Quarantine and kill switch.

### State and queues

- PostgreSQL authoritative state.
- Alembic or equivalent versioned migrations in the Python implementation.
- Transactional job transitions.
- Lease acknowledgment and expiry.
- Idempotency keys.
- Retry-attempt records.
- Transactional outbox.
- Reconciliation workers.
- Dead-letter handling.
- Backup and restore tests.

### Storage

- Quarantine, input, scratch, output, and log storage separated.
- Short-lived job-scoped signed URLs.
- Object size and multipart limits.
- Immutable input manifests and hashes.
- No master storage credentials on providers.
- Output validation before completion.
- Retention schedule and customer deletion path.

### API

- Strict Pydantic models without silent coercion.
- Body, upload, rate, concurrency, and timeout limits.
- Exact CORS allowlist.
- CSRF protection where cookie authentication is used.
- No arbitrary customer URLs to prevent SSRF.
- Generic external errors and structured internal logs.
- Security headers.
- Per-identity quotas.

### Supply chain

- Lock dependencies.
- Pin CI actions by immutable commit.
- Fail CI on secret and high/critical production findings.
- Generate SBOMs.
- Sign provider-agent and runtime releases.
- Verify image signature and digest before execution.
- Use provenance and controlled release promotion.
- Monitor and patch runtime, kernel, hypervisor, and GPU-driver vulnerabilities.

Security references:

- NIST SP 800-190: <https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-190.pdf>
- NIST SSDF SP 800-218: <https://csrc.nist.gov/pubs/sp/800/218/final>
- OWASP API Security Top 10: <https://owasp.org/API-Security/>

## 19. Metering and provider fraud

Metering must combine independent evidence:

- control-plane lease and lifecycle timestamps;
- provider-signed lifecycle events;
- object-storage transfer events;
- customer-visible progress;
- gateway request/token counts for inference;
- bounded GPU runtime evidence;
- random benchmark/canary work;
- anomaly detection;
- settlement reconciliation.

A file hash proves which output was returned, not that the provider honestly performed the work. Validate output structure and use duplicate spot execution for selected/high-value jobs.

## 20. Incident response

Before paid beta:

1. Define severity levels and incident commander.
2. Maintain customer, provider, payment, security, privacy, counsel, insurer, and CERT-In contacts.
3. Prepare containment actions: revoke key/certificate, disable provider, stop job class, block deployment, freeze payout.
4. Preserve time-synchronized evidence.
5. Prepare customer/provider/regulator notification templates.
6. Run a tabletop exercise.
7. Run a backup restoration drill.
8. Record remediation and update the risk register.

A six-hour CERT-In requirement makes "we will write the process after an incident" unacceptable.

## 21. Required legal and operating documents

Before paid beta:

1. Incorporation and founder IP assignments.
2. Customer Terms of Service.
3. Provider Agreement.
4. Acceptable Use Policy.
5. Privacy Notice.
6. Data Processing Addendum.
7. Subprocessor list.
8. Retention/deletion schedule.
9. Refund and dispute policy.
10. Grievance/takedown policy.
11. Incident response and CERT-In procedure.
12. Law-enforcement request procedure.
13. Model/software licence register.
14. Provider onboarding/KYC procedure.
15. Payment, chargeback, reconciliation, and payout procedure.
16. CA-approved GST/TDS position.
17. Responsible disclosure policy.
18. Business continuity and backup procedure.
19. Community-provider privacy/risk disclosure.
20. Cyber/E&O insurance review.

Templates alone do not satisfy these gates. The corresponding technical and operational controls must work.

## 22. Practical delivery phases

### Phase 0 — demo only

Allowed:

- frontend preview;
- synthetic data;
- contract tests;
- local heartbeat and matching;
- test scenes.

Blocked:

- public marketplace API;
- customer files;
- payment;
- external providers;
- untrusted execution.

### Phase 1 — controlled Blender engineering slice

Exit evidence:

- one controlled Linux GPU;
- pinned Blender image;
- signed input/output flow;
- isolated real render;
- cancellation and timeout;
- no-network proof;
- output validation;
- scratch cleanup;
- malicious script/resource tests contained;
- no payment.

### Phase 2 — closed unpaid beta

Exit evidence:

- authentication and authorization;
- PostgreSQL persistence;
- queue leases and retries;
- provider mTLS;
- object-storage policy;
- audit events;
- provider and customer agreements;
- privacy/AUP/grievance workflow;
- manual approvals;
- incident drill;
- external sandbox review plan.

### Phase 3 — paid India Blender beta

Exit evidence:

- payment processor contract;
- append-only ledger;
- reservation and hard cap;
- refunds;
- idempotent webhooks;
- daily reconciliation;
- provider KYC/payout verification;
- CA-approved tax flow;
- backup restoration;
- external penetration/sandbox assessment;
- launch policies published;
- support and dispute workflow operating.

### Phase 4 — multiple providers

Exit evidence:

- signed agent updates;
- independent capacity verification;
- reputation and quarantine;
- canary jobs;
- payout delay;
- abuse-response drill;
- customer community-provider disclosure;
- driver/licence basis documented per node.

### Phase 5 — managed inference

Exit evidence:

- one exact model revision approved;
- gateway-owned API keys;
- prompt-retention control;
- token/usage reconciliation;
- healthy-route and failover tests;
- model licence and prohibited-use enforcement.

### Phase 6 — workstations

Exit evidence:

- OS/application/driver rights;
- ephemeral dedicated-GPU VM;
- encrypted streaming;
- credential isolation;
- project save/checkpoint;
- teardown and GPU reset;
- reconnect and billing evidence.

### Phase 7 — gaming

Entry requires written platform/publisher rights, title-specific anti-cheat support, OS/driver licensing, credential safety, and counsel approval. The correct outcome may be to keep gaming permanently disabled.

## 23. Go/no-go gates

### Real money

Do not accept it until:

- durable state;
- authentication/authorization;
- append-only ledger;
- idempotent processor webhooks;
- hard spending cap;
- refunds;
- reconciliation;
- customer/provider contracts;
- CA-approved tax handling;
- disputes and support.

### Independent home providers

Do not onboard them until:

- KYC and provider agreement;
- node mTLS identity;
- signed agent/update path;
- tested isolation and egress;
- quarantine;
- canary/audit capability;
- cleanup evidence;
- driver licence basis;
- incident response;
- customer disclosure.

### Model hosting

Do not enable a model until:

- exact revision/digest pinned;
- hosted commercial use permitted;
- redistribution/caching rights reviewed;
- runtime approved;
- retention disclosed;
- prohibited uses enforceable;
- usage metering reconciled.

### Gaming

Do not enable a title until:

- documentary rights evidence;
- platform and publisher terms permit the exact design;
- anti-cheat compatibility is supported rather than bypassed;
- OS and GPU driver licences permit deployment;
- credential flow avoids marketplace custody;
- counsel approves the configuration.

## 24. Repository security scan findings

The initial local npm audit found:

- root workspace: one high, three moderate, and one low finding;
- frontend: one high finding.

Local lockfile remediation reduced production dependency audits to zero reported vulnerabilities and the frontend full audit to zero. One low development-time transitive `esbuild` issue remained through `tsx`. Those lockfile changes are intentionally not included in the research-only commit containing this document.

The existing CI security job also contained fail-open behavior and mutable scanner references. Recommended changes are:

- fail on secret findings and redact evidence;
- fail on high/critical production dependency findings;
- fail on high/critical Trivy findings;
- pin actions and scanners;
- enable Dependabot for npm, actions, and container references;
- preserve SBOM and provenance artifacts.

The latest inspected Gitleaks CI artifact contained zero reported findings, but secret rotation and prevention remain mandatory.

## 25. What remains external

The following cannot be completed by repository changes alone:

- binding Indian legal opinion;
- verified final DPDP Rules/commencement schedule;
- NVIDIA commercial-hosting permission or licence interpretation;
- publisher/Valve/anti-cheat permission;
- Windows/application hosting rights;
- CA-approved GST/TDS/payment structure;
- external penetration and GPU sandbox assessment;
- insurance underwriting;
- commercial demand and provider-supply validation.

## 26. Final decision

Proceed with the startup, but narrow the first real product to a managed Blender-render outcome rather than a generic decentralized GPU marketplace.

The immediate sequence is:

1. Preserve the current frontend as an honest preview.
2. Implement the Python backend contract-first without deleting the TypeScript reference prematurely.
3. Add durable identity, state, lease, storage, and audit foundations.
4. Prove one isolated render on one controlled GPU without money.
5. Complete legal, CA, incident, and sandbox gates.
6. Run a small India-only paid Blender beta.
7. Add verified providers slowly.
8. Treat inference, workstations, and gaming as separate permissioned expansions.

"Decentralized" is an infrastructure choice, not a customer benefit. The customer-facing promise should be a reliable, bounded, auditable result at a clear maximum price.
