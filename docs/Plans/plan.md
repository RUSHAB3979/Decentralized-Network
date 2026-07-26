# Authorized Cloud Gaming & Compute Marketplace

## Decision-Gated Product and Engineering Plan

**Status:** Founder operating plan · revised 2026-07-26
**Owner model:** Solo builder, manual coding, AI used only for planning/review
**Planning horizon:** Gates and evidence—not calendar promises
**Scope:** A lawful, safe way to validate remote interactive gaming before considering a marketplace or general compute.

> **The venture is not “rent strangers’ Steam libraries.”** The initial product is an authorized remote-gaming service using dedicated, trusted hosts. A paid public marketplace is permitted only when title rights, host safety, network privacy, and unit economics have passed the gates below.

---

## 1. Executive decision

### 1.1 The problem

A consumer with a weak device cannot reliably use high-end interactive software. A Provider has underutilized capable hardware. The platform can coordinate identity, availability, sessions, safety controls, metering, and support without carrying the media workload itself.

### 1.2 The original opportunity, narrowed correctly

The long-term opportunity remains a two-sided marketplace for GPU-backed interactive sessions and, later, batch compute. The near-term risk is treating four unproven claims as solved:

1. remote gaming works at acceptable quality;
2. a Provider can safely expose a host;
3. game/store rights permit the proposed commercial use; and
4. supply, demand, relay cost, and payouts create positive contribution margin.

This plan proves those claims in order. It never uses “BYOL” as a substitute for title-specific commercial permission.

### 1.3 Non-negotiable launch constraints

| Constraint | Decision |
|---|---|
| Game rights | No paid/public availability for a title unless written authorization or counsel-approved, documented rights evidence exists. |
| Store accounts | Never share, rent, transfer, or collect a Provider’s or Consumer’s store credentials. |
| Host class | Initial alpha hosts are dedicated test machines or managed trusted fleet hardware—not a Provider’s everyday personal computer. |
| Safety claim | Window capture and input filtering are defense-in-depth, not a security boundary. The product makes no stronger claim. |
| Media | Reuse/evaluate proven components; do not begin a greenfield C++ media stack. |
| Networking | TURN is a first-class reliability and cost dependency; never rely on public/free TURN infrastructure. |
| Payments | No money moves until the session ledger, refund policy, jurisdiction, payment-provider availability, and Provider onboarding route are designed and tested. |
| Compute | General compute is a separate product/security decision after gaming has earned it. |

### 1.4 Explicit stop / pivot criteria

Stop or pivot the gaming marketplace path if any condition is true:

- no commercially usable, rights-cleared title or partner path exists;
- the selected media stack cannot meet the internal quality gate on representative networks;
- dedicated-host safety cannot be made acceptable for an invite-only alpha;
- more than 20% of representative attempts require relay and the modeled relay cost cannot fit pricing; or
- trusted Provider supply does not remain online long enough to serve real testers.

A failed gate is useful evidence, not a reason to add features.

---

## 2. Product definition and beachhead

### 2.1 Product lanes

| Lane | What it is | Who may use it | Money | Exit condition |
|---|---|---|---|---|
| **Technical demo** | Remote-streaming proof on owned/trusted machines | Founder and explicit test participants | None | Media, safety, and session telemetry proven |
| **Authorized gaming beta** | Limited catalog of titles with documented permission path | Invite-only Consumers and approved Providers | Optional only after payment gate | Repeatable safe, supported sessions |
| **Marketplace** | Multi-Provider matching and payouts | Public or broader cohort | Yes | Legal, trust, economics, operations all proven |
| **Compute** | Isolated batch jobs on Provider hardware | Separate opt-in cohort | Separate | Independent sandbox/security acceptance |

The technical demo may use a test application, open-licensed game, or title only where every participant is authorized. It is not evidence that a commercial title is cleared.

### 2.2 Beachhead record — must be locked before external alpha

Do not choose “all gamers.” Fill and approve this record first:

| Field | Decision to record |
|---|---|
| Initial geography | One country/region with nearby Providers and a viable payment route |
| Consumer segment | One observable group with a shared acquisition channel |
| Provider source | Named trusted hosts, gaming cafés, or managed fleet—not anonymous supply |
| Authorized initial title(s) | One to three titles with title-review records |
| Host hardware baseline | GPU, encoder, RAM, network uplink, Windows version, driver range |
| Client baseline | Supported desktop browsers, input devices, bandwidth and latency expectations |
| Beta capacity | Maximum concurrent sessions and support owner |
| Privacy/residency posture | Data locations, retention, support/log access, consent text |

### 2.3 Value hypotheses to test

| Hypothesis | Evidence required | Falsification signal |
|---|---|---|
| Consumers value remote play | At least 10 invited testers complete sessions and state a willingness-to-use/willingness-to-pay range | Most testers abandon despite technically successful sessions |
| Providers will supply capacity | At least 3 approved hosts maintain agreed availability for four weeks | Hosts are routinely unavailable or require manual rescue |
| Browser client is viable | Measured end-to-end sessions meet the alpha quality threshold | Codec/input/browser limitations dominate complaints |
| Economics may work | Measured relay, support, payment, and payout assumptions fit a proposed price | Contribution margin remains negative under conservative assumptions |

---

## 3. Legal, title, and account policy

### 3.1 Operating rule

A game appears in the commercial catalog only after the platform has a **Title Approval Record**. The standard Steam Subscriber Agreement licenses Steam content for personal, non-commercial use and restricts renting, licensing, hosting, and commercial exploitation unless permission is otherwise provided. Therefore, ownership of a game by a Consumer or Provider alone is not clearance for this service. See source **S1**.

This is product risk management, not legal advice. Retain qualified counsel in the launch jurisdiction before commercial release.

### 3.2 Title Approval Record

Every candidate title contains the following immutable versioned record:

```text
title_id
publisher / rights holder
store(s) and applicable current terms URL
rights_basis: written_permission | platform_program | counsel_approved | internal_demo_only | blocked
rights_evidence_uri and review_date
reviewer and escalation owner
account_model: consumer_owned | provider_owned_authorized | other_authorized_model
commercial_status: approved | conditional | blocked | expired
multiplayer / anti-cheat status
technical launch profile version
capture profile version
host requirements
regions allowed
support tier: experimental | supported | suspended
expiry / re-review date
```

`byol_allowed` is deliberately not a legal status. A record lacking evidence is `blocked` for commercial use.

### 3.3 Account and game policy

- The platform never asks for or stores store-account passwords, tokens, or MFA codes.
- The platform never provides shared accounts, account farming, cracked binaries, license bypasses, or automated account activity.
- The platform never claims a title is supported because it merely launches or streams.
- Multiplayer and anti-cheat are opt-in per title only after compatibility and rights review.
- A title can be suspended immediately if terms, rights evidence, technical safety, or publisher guidance changes.

### 3.4 Commercial readiness legal gate

Before the first paid session, require all of:

1. counsel-approved service terms, Provider agreement, privacy notice, refund/dispute policy, and acceptable-use policy;
2. title approval records for every commercial title;
3. confirmation that the selected payment/payout provider supports the business and launch geography;
4. age-rating/minor policy and jurisdictional tax review; and
5. incident contact and takedown process.

---

## 4. Threat model and safety posture

### 4.1 Assets and trust boundaries

```text
Consumer browser ── TLS/WSS ── Orchestrator ── authenticated outbound channel ── Provider Agent
      │                              │                                      │
      └──── WebRTC: direct only when policy permits; otherwise relay ────────┘
                                                                     │
                                                            Media host / game
```

Trust boundaries: browser↔orchestrator, agent↔orchestrator, client↔media path, agent↔media host, and deployment/update pipeline. Threat modeling must be updated whenever a boundary or privilege changes, following the OWASP approach in **S4**.

### 4.2 Threats, controls, and residual risk

| Threat | Required controls before external alpha | Residual risk / decision |
|---|---|---|
| Malicious Consumer affects Provider host | Dedicated host; non-admin game user; no shell/file-transfer/clipboard/desktop controls; process and launch allowlists; session maximums; emergency stop | Games and legacy Windows software remain complex; ordinary personal PCs are excluded |
| Consumer sees Provider data | Dedicated machine; window/process capture binding; clean profile; no Provider personal data; preflight capture test | Capture bugs are possible; Provider agrees to dedicated-host restriction |
| Compromised/rogue agent | Per-device enrollment; short-lived credentials; command authorization; signed releases; revoke/kill switch; audit trail | Host compromise cannot be fully prevented by the platform |
| Stolen Consumer session | Short-lived, audience-bound session token; TLS; signaling authorization; no credentials in logs | Client compromise remains user-side risk |
| Peer network/privacy exposure | Relay-only public-beta default until a documented privacy review permits direct P2P; disclose connection behavior | Direct P2P is an explicit later product decision |
| Abuse, fraud, chargebacks | Invite-only users; rate limits; immutable metering; holds; delayed payouts; support review | Public fraud controls are a scale-phase problem |
| Malicious update/dependency | Locked dependencies; SBOM; signed artifact and update manifest; staged rollout; rollback | Dependency zero-days remain possible |
| Hardware damage / thermal event | Telemetry; per-node temperature/power policy; autonomous end/cooldown; no override by Consumer | Sensor availability differs by hardware |

### 4.3 Dedicated-host baseline

Initial Provider machines must:

- have no personal files, personal browser profile, personal passwords, or personal work account access;
- use a separate non-administrator Windows account for the service and games;
- accept only allowlisted launch profiles and signed agent commands;
- have automatic OS/game updates governed by a tested maintenance window;
- report health, driver version, thermal state, and available capacity; and
- be able to disconnect or kill every session locally.

AppContainer/Windows Sandbox are research inputs, not assumed production solutions: legacy games and anti-cheat may not operate under them. Microsoft documents AppContainer as a restricted process environment and Windows Sandbox as disposable isolation; compatibility must be tested title-by-title (**S6**).

### 4.4 Incident standards

| Event | Immediate action | Evidence | Recovery gate |
|---|---|---|---|
| Unauthorized input/capture suspicion | End session, revoke session token, disable node | session events, agent/media logs, version IDs | Security review approves re-enable |
| Agent compromise suspicion | Revoke node identity, block update channel, quarantine host | binary hash, host logs, signed release provenance | Host rebuilt/re-enrolled |
| Financial dispute | Freeze related payout/ledger entries | immutable meter/event chain | Support decision and documented refund |
| Thermal limit or repeated crash | End session, cooldown node | hardware snapshot and process exit | automated health check passes |

---

## 5. Architecture: small now, evolvable later

### 5.1 Components and ownership

| Component | Responsibility | Initial technology | Must not do |
|---|---|---|---|
| Orchestrator | Auth, enrollment, catalog, matching, state machine, session commands, metering events | Python/FastAPI + PostgreSQL | Encode media or hold game credentials |
| Provider Agent | Hardware scan, heartbeat, command validation, lifecycle supervision, local kill switch | Python v0 | Accept arbitrary shell commands or unapproved executables |
| Media adapter | Launch an evaluated host stack; expose bounded lifecycle/status interface | Thin adapter around selected stack | Become a new streaming engine |
| Web client | Session request, signaling, playback, bounded input, consent and diagnostics | Browser/WebRTC | Bypass server authorization |
| TURN/STUN | Authenticated ICE service and relay capacity | Managed or operated service | Be a free/public shared dependency |
| Observability | Correlated logs, metrics, traces, audit events | Structured service | Store secrets, raw game video, or input content by default |

### 5.2 Media-stack decision gate

Do not assume Sunshine is a browser-WebRTC host. Sunshine is primarily a Moonlight/GameStream-compatible host and GPLv3; its web interface is configuration/pairing rather than an official browser game-streaming client. Treat it as one candidate, review license obligations, and run an integration spike before selecting it (**S3**).

**Spike candidates:**

1. a proven host with a supported browser/WebRTC media path;
2. a thin bridge/adaptor only if its license, maintenance, and latency meet requirements; and
3. native-client fallback for the technical demo if browser viability fails.

**Spike acceptance:** demonstrate ten repeatable remote sessions on two representative network paths; collect time-to-first-frame, resolution/fps, RTT, bitrate, codec, input behavior, direct/relay result, and failure reason. Choose or reject a stack in a written ADR. No production media implementation before this decision.

### 5.3 WebRTC requirements

WebRTC does not prescribe signaling; it needs a separately authorized signaling service and ICE servers. STUN/TURN candidates are exchanged through signaling, and TURN relays traffic when direct connectivity fails (**S2**). The system therefore requires:

- authenticated signaling messages scoped to one session and one peer role;
- ephemeral TURN credentials scoped by expiry, session, and quota;
- trickle ICE support and explicit connection-state timeouts;
- metrics for direct versus relay connection, selected candidate class, connection duration, and disconnect reason;
- an admission policy based on measured network preflight, not optimistic matching; and
- relay capacity/cost modeled before public launch.

### 5.4 Control-plane protocol invariants

- A node receives an opaque immutable `node_id`; human-readable names are metadata only.
- Enrollment is single-use and short-lived. The agent generates a device keypair locally; the control plane binds the public key to a node after approval.
- Agent-to-orchestrator communication is outbound initiated; the platform never opens an arbitrary inbound management port on a Provider host.
- Every command has `command_id`, `session_id`, expected state/version, expiry, issuer, and signature/authorization context.
- Commands are idempotent. The agent persists command outcome before acknowledging it.
- A session cannot become `live` until both agent and media adapter report the expected state.
- A missing heartbeat ends the lease; it does not prove the host process stopped. Reconciliation is mandatory.
- Every state transition emits an append-only audit event with correlation IDs.

### 5.5 Core data model

| Entity | Invariants |
|---|---|
| User | One account can hold Consumer and Provider roles; status, consent, and risk state are explicit |
| ProviderOrganization | Owns nodes, payout identity later, policy and support contacts |
| ProviderNode | One enrollment identity, desired/observed state, capacity lease, software/driver compatibility |
| HardwareSnapshot | Timestamped and versioned; never treated as permanent truth |
| GameTitle / TitleApproval | Catalog metadata separated from rights evidence and technical profile version |
| ProviderGameInstall | Verified install/technical profile observation, not proof of commercial rights |
| Session | Immutable request + authoritative lifecycle; one active lease per constrained resource |
| SessionCommand | Idempotency and reconciliation record |
| MeteringEvent | Append-only event source; computed invoice is derived, never hand-edited |
| AuditEvent | Security and lifecycle evidence, retention class, correlation ID |
| PaymentLedger / Payout | Future, double-entry-like immutable accounting records; never inferred from client reports |

### 5.6 State machines

```text
Session:
requested → eligibility_checked → offered → accepted → reserved → launching
→ signaling → connecting → live → ending → cleaned → completed
                                  ↘ failed
                                  ↘ cancelled

Node:
pending_approval → enrolled → online_idle → reserved → launching → streaming
→ draining → online_idle
       ↘ quarantined / revoked / maintenance / error_cooldown
```

Only the orchestrator advances authoritative business state. The agent reports observed facts; reconciliation resolves disagreement. `cleaned` requires cleanup evidence before the resource returns to `online_idle`.

---

## 6. Quality, reliability, and economics

### 6.1 Quality measurements

Do not use “playable” as the sole metric. Store per session:

- request-to-offer, offer-to-launch, launch-to-first-frame, and total time-to-first-frame;
- selected video codec, resolution, frame rate, bitrate, packet loss, RTT/jitter where available;
- direct/relay path and relay bytes;
- input capture/injection errors;
- game/stream-host exit cause;
- Consumer and Provider post-session quality score; and
- all software/driver/profile versions.

### 6.2 Gates, not false precision

| Gate | Minimum evidence | Outcome |
|---|---|---|
| Technical demo | 10 instrumented sessions, two network conditions, clean session termination | Select/reject media stack |
| Internal alpha | 20 sessions across at least 3 dedicated hosts; ≥80% reach `live`; every failure categorized | Fix dominant failure modes |
| Invite beta | 50 sessions with approved users; stable host operation; no unresolved high-severity safety incident | Decide whether to broaden cohort |
| Paid beta | Approved title rights; ledger reconciliation; conservative unit economics; refund/payout process tested | Enable restricted payments |

Targets become stricter only after baseline measurements. The plan avoids inventing latency thresholds before a real network/host baseline exists.

### 6.3 Unit economics model

For each session, calculate before payment launch:

```text
net contribution = consumer charge
                 - payment processing and refund reserve
                 - Provider earning / incentive
                 - TURN relay egress and infrastructure
                 - support, fraud, and operational allocation
```

Report relay percentage, median relay bytes, support minutes/session, failed-launch cost, gross margin before/after Provider earning, and payout reserve. If the conservative model is negative, do not solve it with opaque pricing or scale.

### 6.4 Payments boundary

A marketplace payment system includes connected accounts, onboarding/KYC, charges, transfers, and payouts; use a provider’s marketplace product rather than storing payment data or implementing payouts yourself. Stripe Connect is one candidate, subject to geography and business approval (**S5**).

Paid launch requires:

- idempotent payment and webhook handling;
- a session ledger reconciled against authoritative lifecycle events;
- holds/authorization policy, cancellation policy, refund route, and dispute freeze;
- delayed/reviewable Provider payouts; and
- tax, KYC, sanctions, and age obligations reviewed for the chosen jurisdiction.

---

## 7. Milestone roadmap

### M0 — Local control-plane hello world

**Goal:** developer can run Postgres, orchestrator health, and an agent health ping locally.

**Exit:** reproducible local setup; health endpoint distinguishes API and database failure; no secret in Git; basic test/smoke instructions work.

**Not included:** remote process launch, public exposure, marketplace logic, or stream host.

### M1 — Provider identity and observed availability

**Goal:** safely know whether an approved dedicated node is available.

**Scope:** enrollment flow, node approval/revocation, agent config, heartbeats, hardware snapshot, TTL/offline transition, audit events, and migrations.

**Exit:** a node is online only while a valid lease is renewed; revoked nodes reject new commands; lost-heartbeat state is visible and reconciled.

### M2 — Media feasibility spike

**Goal:** prove or disprove selected remote-media path before building a marketplace.

**Scope:** one test application/authorized title, one trusted host, browser or declared native fallback, authenticated signaling, TURN test, telemetry harness, media-stack ADR.

**Exit:** ten instrumented sessions demonstrate selected media path; direct and relay behavior are measured; a build-versus-integrate decision is recorded.

### M3 — Safe internal session vertical slice

**Goal:** request → approved match → bounded launch → stream → end → cleanup → evidence.

**Scope:** session state machine, resource lease, command idempotency, launch/capture/input policy, local kill switch, cleanup evidence, reconciliation, failure UX.

**Exit:** three dedicated hosts complete 20 internal sessions with categorized failures; the host cannot launch arbitrary programs through the platform.

### M4 — Rights and beta readiness

**Goal:** transform a technical demo into a lawful, bounded product candidate.

**Scope:** title approval record, counsel review, terms/policies, threat model, incident runbook, signed agent/update plan, privacy and retention decisions, cohort selection.

**Exit:** all commercial-readiness requirements in Section 3.4 are approved. If no title is approved, remain an internal technical demo; do not workaround the restriction.

### M5 — Invite-only authorized beta

**Goal:** validate experience, supply reliability, and support burden with a small controlled cohort.

**Scope:** invite flow, trusted Providers, support queue, session feedback, network preflight, quality dashboard, relay monitoring, manual risk review.

**Exit:** at least 50 sessions meet the invite-beta gate, Provider availability is measured for four weeks, and the economics model uses observed—not assumed—inputs.

### M6 — Restricted paid beta

**Goal:** validate payment/Provider economics without public-marketplace scale.

**Scope:** payment-provider integration, ledger, refunds, payouts, fraud rules, terms acceptance, operational reconciliation.

**Exit:** finance-critical paths survive failure/retry scenarios without duplicate charge, unpaid usage, or unjustified payout.

### M7 — Scale only after repeatability

**Goal:** expand geography/cohort without hiding reliability debt.

**Scope:** regional matching, TURN capacity, staged agent rollout, SLOs, backups, DDoS/rate-limit posture, incident drills, support operations.

**Exit:** load-tested control plane, documented relay cost model, and error-budget/SLO ownership.

### M8 — Compute feasibility, separately approved

**Goal:** decide whether untrusted batch compute deserves a new product line.

**Scope:** isolated test jobs, artifact path, GPU allocation, sandbox escape testing, full threat model, separate pricing/legal review.

**Exit:** an untrusted test job cannot access host home data or undeclared network/filesystem resources. Failure ends or redesigns the compute path.

---

## 8. Engineering operating system

### 8.1 Repository and delivery standards

- component README, local runbook, `.env.example`, and no live secrets in source control;
- pinned dependencies and lockfiles;
- formatter/linter/type checking appropriate to each component;
- unit tests for state transitions, authorization, idempotency, and policy parsing;
- integration tests for agent enrollment/heartbeat/TTL and session reconciliation;
- smoke test for the one current milestone; and
- CI generates an SBOM and checks dependencies. OWASP highlights supply-chain risks, artifact integrity, and component inventory as ongoing concerns (**S4**).

### 8.2 Required ADRs

1. **ADR-001:** central control plane with decentralized media; trust boundaries.
2. **ADR-002:** commercial title approval policy; account and rights rules.
3. **ADR-003:** media-stack decision after M2 spike, including license analysis.
4. **ADR-004:** node enrollment, credentials, command authorization, and revocation.
5. **ADR-005:** P2P versus relay privacy/cost policy.
6. **ADR-006:** payment/payout provider and ledger model before M6.
7. **ADR-007:** whether compute proceeds after M8 feasibility.

### 8.3 Definition of done for any milestone

A milestone is done only when:

1. the stated exit evidence exists;
2. failure/retry behavior is observable;
3. a demo/smoke test exercises the changed path;
4. sensitive data and secrets are handled according to policy;
5. known risks are recorded with an owner and review date; and
6. the next milestone’s prerequisite decision is explicit.

---

## 9. Metrics dashboard

### 9.1 Product and quality

- eligible-request rate;
- request-to-first-frame percentiles;
- reach-`live` rate and completion rate;
- direct/relay ratio and relay bytes/session;
- RTT/jitter/loss where available;
- crash, cleanup, and re-match rates;
- Consumer and Provider satisfaction; and
- title/host/software-version correlation with failures.

### 9.2 Marketplace and economics

- approved Providers, weekly host-hours, scheduled vs available capacity, utilization;
- consumer activation and return rate;
- Provider retention and maintenance burden;
- gross transaction volume only after payments;
- contribution margin per completed session; and
- refund, dispute, fraud, and delayed-payout rate.

### 9.3 Security and operations

- agent enrollment/revocation events;
- rejected command/policy violations;
- high-temperature terminations;
- security incident count and recovery time;
- signed-release adoption, rollback rate, and dependency-alert remediation; and
- backup restore and incident drill results.

Metrics are privacy-minimized. Raw gameplay, keystrokes, credentials, and personal desktop content are not telemetry.

---

## 10. Decision log

| Decision | Current choice | Revisit trigger |
|---|---|---|
| First commercial gaming path | Authorized titles only; internal demo otherwise | Written rights/counsel result |
| First host class | Dedicated trusted/managed hardware | Proven isolation, insurance, and support model |
| First client | Browser if M2 succeeds; native fallback allowed for technical evidence | Browser compatibility/quality result |
| Media strategy | Evaluate/reuse; no greenfield engine | M2 ADR |
| Networking | Relay-first public-beta posture; direct P2P requires privacy review | M2/M5 connection and cost evidence |
| Control plane | Python + PostgreSQL | Measured operational constraint, not preference |
| Agent | Python v0 with least privilege | Packaging/telemetry/security evidence |
| Payments | After measured quality and legal gate | M5 economics and payment-provider approval |
| Compute | Separate optional future lane | M8 isolation feasibility |
| Blockchain | Out of scope | A demonstrated requirement, not hype |

---

## 11. Research basis and source register

Research was reviewed on **2026-07-26**. Sources establish technical and contractual constraints; they are not legal advice.

| ID | Source | Plan implication |
|---|---|---|
| **S1** | [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/) | Steam grants personal, non-commercial use and restricts rental/licensing/hosting/commercial exploitation without permission. Commercial title availability requires a separate rights basis. |
| **S2** | [WebRTC: peer connections](https://webrtc.org/getting-started/peer-connections) | Signaling is application-defined; ICE requires STUN/TURN candidate exchange; TURN is a normal commercial connectivity dependency. |
| **S3** | [Sunshine documentation](https://docs.lizardbyte.dev/projects/sunshine/latest/) and [Sunshine license](https://github.com/LizardByte/Sunshine/blob/master/LICENSE) | Sunshine is an evaluated host candidate, not a presumed browser-WebRTC solution; GPLv3 obligations require review before integration/distribution. |
| **S4** | [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling) and [OWASP Software Supply Chain guidance](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html) | Trust boundaries, signed artifacts, dependency inventory, and staged updates are roadmap requirements. |
| **S5** | [Stripe Connect documentation](https://docs.stripe.com/connect) | Marketplace charges, connected-account onboarding, transfers, and payouts are a specialist payment workflow; do not build them from scratch. |
| **S6** | [Microsoft AppContainer isolation](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation) and [Windows Sandbox](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-overview) | Windows isolation options exist but game/anti-cheat compatibility is not assumed; dedicated hosts remain the initial safety baseline. |

---

## 12. Immediate next actions

1. Keep the current M0 scope: local database, orchestrator health, agent health ping, repository hygiene.
2. Create ADR-001 and ADR-002 before adding remote launch capability.
3. Define the beachhead record in Section 2.2; leave unknowns explicit rather than inventing them.
4. Build M1 node enrollment/heartbeat only after M0 is demonstrably complete.
5. Plan M2 as a bounded media feasibility spike with a test application or rights-cleared title.
6. Contact qualified counsel/rightsholders before describing any commercial gaming catalog or accepting payment.
7. Do not begin general compute, public Provider onboarding, or payments while a preceding gate is unresolved.

---

## One-line strategy

**Prove a safe, measured remote interactive session on dedicated trusted hardware; commercialize only where title rights, host protection, network privacy, support capacity, and contribution margin are evidenced—not assumed.**
