# Human Roles Blueprint — P2P Compute & Cloud Gaming Marketplace

**Date:** August 8, 2026
**Scope:** Every human role required to build, launch, and scale the platform — what each role does, what they own in this repo, and what they must study to be competent.
**Companion docs:** `docs/PLAN.md` (phased milestones), `SAFE-EXECUTION-PLAN.md` (phase gates), `RISK-REGISTER.md` (threat map), `docs/AISmartUsage.md` (AI model assignments).

---

## How to Read This Document

Each role has four sections:

- **Mission** — the one-sentence reason this role exists.
- **What You'll Build / Own** — concrete responsibilities mapped to files, systems, and Risk Register IDs.
- **What to Study** — the exact learning path (topics → resources → certifications).
- **Key Deliverables** — the observable output that proves the role is doing its job.

Roles are grouped into three squads:

| Squad | Roles | Purpose |
|---|---|---|
| 🛠️ **Engineering Squad** | Roles 1–10 | Build the platform |
| ⚖️ **Legal, Finance & Compliance Squad** | Roles 11–15 | Keep the company legal and solvent |
| 🚀 **Product & Growth Squad** | Roles 16–20 | Fill both sides of the marketplace |

---

## Current Engineering Assignments

Assigned 2026-08-10, redistributed the same day (see below). GitHub handles are
the repo collaborators; `.github/CODEOWNERS` mirrors this table by path so review
requests route automatically. **If this table and CODEOWNERS ever disagree,
CODEOWNERS wins and this table is the bug.**

Execution detail — first tasks, sequencing, and clash rules — lives in
[TEAM-EXECUTION-PLAN.md](./TEAM-EXECUTION-PLAN.md).

| Owner | Roles | Primary surface |
|---|---|---|
| [@RUSHAB3979](https://github.com/RUSHAB3979) | **R1** Architect + **R5** Orchestrator *(M0 only)* | `orchestrator/`, `packages/contracts/`, all interface decisions |
| [@YogitaKanwar](https://github.com/YogitaKanwar) | **R3** Cloud/Platform + **R9** Database → **R5** after M0 | `.github/`, `docker-compose.yml`, schema + migrations — task list: [yogitatasks.md](./yogitatasks.md) |
| [@Shubh-tech-grow](https://github.com/Shubh-tech-grow) | **R2** Network & Streaming + **R6** Provider Agent | `agent/`, streaming/TURN, telemetry — task list: [shubhtasks.md](./shubhtasks.md) |
| [@ryujikentaro](https://github.com/ryujikentaro) | **R4** Security & Sandbox + **R10** SRE | Threat model, sandbox, CI security gates, runbooks — task list: [ryujitasks.md](./ryujitasks.md) |
| [@AdarshNarwankar](https://github.com/AdarshNarwankar) | **R8** Frontend + **R7** Payments *(when it starts)* | `web-client/` — task list: [adarshtasks.md](./adarshtasks.md) |

### Why this shape

The first cut put three names on every backend role and one name on frontend.
Measured against the actual repository that was backwards: `web-client/src` is
4,299 lines and `orchestrator/` is 3, so the "small" role was the only one with
real code in it and the "big" ones were co-owned placeholders.

Two rules replaced it:

1. **One primary owner per surface.** Three names on a path means the review
   notification is everyone's job and therefore nobody's.
2. **Pair roles that share a machine or a lifecycle.** The agent and the network
   both run on the provider's box. The database and the infrastructure that
   starts it are one problem. Security and reliability share their runbooks.

`packages/contracts/` stays with R1 even after `orchestrator/` hands over,
because an interface change is a decision that breaks four surfaces at once.

### Now owned, previously open

- **R1** — explicitly founder-held rather than implied by the Founder-Hat
  Mapping. Someone is accountable for matching, leasing, and state transitions.
- **R10** — folded into R4. No production surface exists yet, but the person who
  will be paged is the person who wrote the sandbox.
- **R7** — parked with R8's owner. No payment code exists; the name is there so
  it does not get discovered unowned at Phase 1.

R4's owner carries T-01 and T-04, the two risks the register marks as
platform-killing. That is a lot of blast radius resting on one person; add a
second reviewer on security-relevant changes before launch
(TEAM-EXECUTION-PLAN.md risk P-6).

---

# SQUAD A — ENGINEERING (Roles 1–10)

---

## Role 1 — Distributed Systems Architect

**Mission:** Design the brain of the marketplace — how thousands of untrusted consumer PCs get discovered, scored, matched, and supervised by the central control plane.

**What You'll Build / Own:**
- The node-matching algorithm in `services/orchestrator/src/matching.ts` (including the `rights_basis` hard filter from SEP §3.1).
- The provider registry and TTL-based liveness design in `state.ts` (today in-memory; Phase 1 → PostgreSQL behind a repository abstraction).
- Heartbeat protocol design: cadence, freshness windows, weighted recency scoring (`PLAN.md` §7 risk: stale provider metrics).
- Job scheduling architecture for Phase 2: queue partitioning, lease timeouts, orphan re-queue, backpressure under load.
- The tiered trust model (T0 Compute → T1 Gaming → T2 BYOL AAA) as enforceable matching constraints, not just policy (`RISK-REGISTER` T-05, T-10).
- Latency-aware placement: multi-vantage RTT measurement to defeat region fraud (Risk T-14).

**What to Study:**
- **Fundamentals:** *Designing Data-Intensive Applications* (Kleppmann) — the canonical text for distributed state, partitioning, and consistency.
- **Scheduling:** Google Borg/Omega papers, Kubernetes scheduler internals, queue lease semantics (SQS/RabbitMQ visibility timeout models).
- **Matching algorithms:** Bipartite matching, weighted scoring, marketplace design (Ride-sharing matching papers from Uber/Lyft engineering blogs).
- **P2P discovery:** Kademlia DHT, libp2p concepts (even though our control plane is centralized, provider discovery borrows from P2P literature).
- **Courses:** MIT 6.824 Distributed Systems (free on YouTube), System Design Interview Vol. 1–2 (Alex Xu).

**Key Deliverables:**
1. `matching.ts` upgraded from naive filter to weighted scoring engine.
2. Phase 1 persistence design doc (repository abstraction, schema migration plan).
3. Phase 2 scheduler design doc with lease/backpressure semantics.

---

## Role 2 — Network & Streaming Engineer

**Mission:** Make a stream from a stranger's bedroom PC in Pune feel local to a gamer in Bangalore — and make it impossible to intercept.

**What You'll Build / Own:**
- WebRTC session pipeline (Phase 2): signaling, SDP negotiation, ICE candidate gathering.
- NAT traversal: STUN for direct peer connections, TURN relay fallback for the ~10–20% of NAT-blocked pairs (own the *relay-minutes* metric — it's a top-6 unit-economics risk).
- Media path: WebRTC's mandatory DTLS-SRTP encryption (Risk T-06), NVENC hardware encoding on the provider node, input channel with sanitization.
- Multi-vantage latency probes that override provider self-reported telemetry (Risk T-05 forgery, T-14 region fraud).
- Session continuity design: streams must survive control-plane blips (Risk T-08 — data path peer-to-peer, control path centralized).
- Compute track alternative: resumable high-throughput transfer (pre-signed S3/R2 or tus-style) for multi-GB `.blend` files — **WebRTC is the wrong default for batch compute**.

**What to Study:**
- **WebRTC deeply:** *WebRTC for the Curious* (free, webrtcforthecurious.com) — signaling, ICE, STUN/TURN, DTLS, SRTP.
- **Latency engineering:** Cloud gaming latency budgets (capture → encode → network → decode → display), jitter buffers, packet-loss concealment.
- **Video encoding:** H.264/H.265/AV1 tradeoffs, NVENC SDK, hardware encoder constraints per GPU generation.
- **Real-world reference code:** Study Sunshine + Moonlight (open-source game streaming) — the same tech stack you'll replicate inside the provider agent.
- **Networking basics:** NAT types (full-cone, symmetric), UDP vs TCP head-of-line blocking, QUIC.

**Key Deliverables:**
1. Working WebRTC session between two LAN machines with <40ms glass-to-glass latency.
2. TURN relay deployment with cost-per-minute instrumentation.
3. Egress/relay monitoring dashboard feeding unit economics (`business_plan_review.md` §3.3).

---

## Role 3 — Cloud / Platform Engineer (DevOps)

**Mission:** Everything runs, reproducibly, everywhere — from `docker compose up` on a laptop to production on AWS.

**What You'll Build / Own:**
- `docker-compose.yml` (orchestrator + provider-agent) and the path to Kubernetes for the control plane.
- CI/CD in `.github/workflows/`: lint, typecheck, build, test, signed artifact publishing.
- Signed releases for agent + node images (Risk T-12 supply-chain: lockfiles committed, dependency pinning, reproducible builds — the agent gets the strictest bar).
- Secrets management: vault-backed secrets instead of `.env` files in git (Risk T-07; see SEP §10 action: scrub `.env` from history, rotate Postgres password).
- PostgreSQL provisioning for Phase 1 persistence; backup and restore drills.
- Cloudflare-class CDN/WAF + rate limiting in front of the orchestrator (Risk T-08 DDoS).

**What to Study:**
- **Docker to production:** Official Docker deep-dive, image layer caching, multi-stage builds, distroless images.
- **Kubernetes:** *Kubernetes Up & Running* (Kelsey Hightower) — pods, deployments, services, ingress; cert-manager for mTLS certificates.
- **IaC:** Terraform fundamentals (HCL), or Pulumi if you prefer TypeScript.
- **GitHub Actions:** Reusable workflows, OIDC-based deploys without long-lived cloud keys.
- **Supply-chain security:** Sigstore/cosign for image signing, SBOM generation (Syft), dependency scanning (Trivy, Dependabot).

**Key Deliverables:**
1. One-command reproducible dev environment.
2. Signed CI-built provider agent binaries.
3. Production deployment runbook (ties into `docs/OPERATIONS.md`).

---

## Role 4 — Security & Sandbox Engineer

**Mission:** Ensure a malicious workload can absolutely never harm a provider's machine — and a malicious provider can absolutely never steal a customer's data. T-01 and T-04 are the two platform-killing risks; this role owns both.

**What You'll Build / Own:**
- Sandbox runtime for Phase 4-pulled-forward compute: **gVisor (`runsc`)** or Firecracker/Kata isolation — no privileged containers, no host mounts, dropped capabilities, non-root UID, read-only rootfs, seccomp profiles.
- Per-job egress: default-deny outbound networking with declared-endpoint allowlists; SMTP and C2 patterns always blocked (Risks T-13, L-10).
- Encrypted ephemeral volumes: platform-held keys, verified wipe-on-exit, VRAM scrub + GPU reset between tenants (Risks T-01, T-11).
- Anti-fraud plumbing: signed agent binaries that refuse modified images, heartbeats carrying image hash + agent version (Risk T-05).
- Curated-image allowlist enforcement: v1 runs *your* signed worker images (Blender/PyTorch) with data-only inputs — arbitrary containers stay off the table until v2.
- Canary/audit sessions: synthetic jobs that plant markers and attempt recovery to prove wipes actually happen.

**What to Study:**
- **Container isolation:** gVisor architecture docs, Firecracker design paper, syscall surface analysis, Linux capabilities/seccomp/namespaces deeply.
- **Offensive basics (to defend well):** OWASP Top 10, container-escape CVE history (runC escapes), gVisor bypass attempts in public research.
- **Applied crypto:** TLS/mTLS certificate lifecycles, envelope encryption, key management (KMS/vault).
- **Standards:** MITRE ATT&CK (containers matrix), NIST container security guide (SP 800-190).
- **Certifications (optional but useful):** OSCP for credibility, or Google SRE security chapters.

**Key Deliverables:**
1. Hardened sandbox runner (gVisor + deny-all egress + resource caps) behind a `Runtime` interface.
2. Pre-Phase-1-exit external penetration test scope + remediation plan.
3. Wipe-verification proof system feeding the audit log.

---

## Role 5 — Backend Engineer (Orchestrator)

**Mission:** Turn the control-plane skeleton into production APIs that clients, providers, and admins can trust.

**What You'll Build / Own:**
- `services/orchestrator/src/index.ts` and `config.ts` — every endpoint, validation path, and error contract in `docs/API.md`.
- Phase 1: PostgreSQL-backed repositories replacing in-memory maps (providers, jobs, rights, audit) without breaking the existing API surface (`PLAN.md` Phase 1 exit criteria).
- Phase 2: queue-backed job lifecycle — submit → queued → running → completed/failed with deterministic transitions.
- Phase 3 security hardening: AuthN/AuthZ on **every** endpoint with users/providers/admins separated (currently zero auth — public-exposure blocker, Risk T-07).
- The append-only audit log: sessions, jobs, takedowns, tier changes, payouts — the primary legal defense artifact (SEP §5, Risk L-04).
- TDS/GST invoice generation in the billing path, not by hand (Risk L-09).

**What to Study:**
- **Node.js/TypeScript production patterns:** Fastify (or your chosen framework) plugins, Zod validation (`packages/contracts` shared schemas), structured logging (pino).
- **PostgreSQL:** Indexing, transactions, isolation levels, row-level security; migrations with Drizzle/Prisma/node-pg-migrate.
- **Job queues:** BullMQ (Redis) semantics — retries, backoff, idempotency keys, dead-letter queues.
- **API security:** OWASP API Security Top 10, JWT vs session tradeoffs, refresh-token rotation, rate limiting.
- **Testing:** Contract testing between orchestrator and agent, integration tests with Testcontainers.

**Key Deliverables:**
1. Persistent orchestrator surviving restarts (Phase 1 exit).
2. Auth-gated API surface with audit events on auth failures (Phase 3 exit).
3. 95%+ job completion without manual intervention.

---

## Role 6 — Backend Engineer (Provider Agent)

**Mission:** Build the daemon that turns a stranger's gaming PC into a verified, attested, supervised marketplace node.

**What You'll Build / Own:**
- `services/provider-agent/` — the heartbeat loop, capability advertisement (GPU model, VRAM, encoder support, uplink), metrics payloads.
- NVML integration: real-time GPU temperature/utilization/memory monitoring plus the **thermal kill-switch** (protects provider hardware — market it as "we protect your rig").
- mTLS client-certificate identity: per-node certs issued at onboarding, pinned, rotated (Risk T-06).
- Hardware fingerprinting: GPU model, SMBIOS UUID, MAC — stable identifiers, never randomized or spoofed (Risk T-05, SEP §2.3).
- Session teardown enforcement: teardown checklist executed by the agent, driving ephemeral volume destruction and VRAM scrub (T-01/T-11).
- Provider-side UX: availability windows, workload-category opt-outs, earnings telemetry (SEP §2.6 — *they* need safety features too).

**What to Study:**
- **Systems programming on Windows + Linux:** Service/daemon lifecycle (systemd units, Windows services), process supervision, crash recovery.
- **NVML/CUDA ecosystem:** NVIDIA Management Library bindings, GPU topology, encoder session limits per GPU class.
- **TPM & measured boot:** TPM 2.0 quote/attestation flow, secure boot chain, remote attestation protocols (needed for T1/T2 gaming tiers).
- **Rust (recommended for v2):** Memory safety for a daemon running with elevated privileges on customer hardware.
- **Update systems:** The Update Framework (TUF), signed update channels, rollback protection.

**Key Deliverables:**
1. Self-updating, signed agent with 99%+ heartbeat reliability.
2. Thermal kill-switch validated on real hardware.
3. Attestation flow passing orchestrator verification for T1 admission.

---

## Role 7 — Backend Engineer (Payments & Billing)

**Mission:** Money moves correctly, legally, and auditable — or the company dies regardless of how good the tech is.

**What You'll Build / Own:**
- Licensed payment aggregator integration (Razorpay/Cashfree/PayU): collection, refunds, payout routing — **the platform never custodies funds** (Risk L-08, SEP §1.6).
- Section 194-O TDS deduction in the payout pipeline from payout #1, automated with CA confirmation (Risk L-09).
- GST invoicing on platform fees with a monthly compliance calendar.
- Session-credit auto-refunds triggered by telemetry: session dies → credit lands before the complaint exists (Risk L-07).
- Fraud controls: payment-verified accounts, velocity limits, spend-pattern anomaly flags, chargeback monitoring with auto-freeze (Risks L-10, F-01).
- Provider payout safety: penny-drop bank verification, payout-change cooldown + re-verification (Risk F-02), bond holdbacks per contract structure.

**What to Study:**
- **Razorpay/Cashfree docs deeply:** Route/payout products, webhook idempotency, reconciliation cycles, test-mode behaviors.
- **Indian fintech regulation basics:** RBI payment-aggregator guidelines, PPI boundaries (why you never build wallets/credits as stored value without counsel), §194-O and GST on e-commerce operators.
- **Ledger design:** Double-entry bookkeeping for engineers (many good open posts — e.g., Modern Treasury's ledger series), idempotent money movement, *never* float math on currency.
- **Fraud systems:** Chargeback representment with session evidence, velocity rule design, anomaly detection basics.

**Key Deliverables:**
1. Payout pipeline with correct TDS + invoices from day one.
2. Auto-refund system wired to session telemetry.
3. Chargeback-rate dashboard with auto-freeze threshold.

---

## Role 8 — Frontend Engineer

**Mission:** The "outcome UX" wedge — a creator pastes a file, pays with a card, gets a result. No Docker knowledge, no DevOps. The incumbents sell machines; we sell outcomes.

**What You'll Build / Own:**
- `web-client/` (React + Vite + Tailwind): the entire customer and provider surface.
- Compute flow: upload → quote → progress → download. That simplicity *is* the product.
- `CatalogView` and session views for the gaming track, gating visibly on `rights_basis`.
- Provider dashboard: earnings, availability windows, reputation score display, tier status.
- Real-time state: WebSocket/polling for job progress, session status, refund notifications.
- Provider onboarding flows: KYC handoff, contract e-sign capture, hardware fingerprint consent.

**What to Study:**
- **React fundamentals done right:** Hooks mental model, state colocation vs lifting, React Query for server state.
- **Tailwind + design systems:** Layout primitives, tokens, dark mode, accessibility (WCAG 2.1 AA).
- **File upload engineering:** Resumable uploads (tus protocol), chunked multipart with progress, Workers for hashing.
- **WebRTC client basics** (for Phase 2): `RTCPeerConnection` in browser, fallback handling, streaming stats overlays.
- **Performance:** Code splitting, virtualized lists, Core Web Vitals measurement.

**Key Deliverables:**
1. <15-minute time-to-first-result for a new customer (business plan metric #6).
2. Provider earnings dashboard that becomes the #1 supply-side retention tool.
3. Mobile-responsive catalog + session UI.

---

## Role 9 — Database / Data Engineer

**Mission:** The audit log is the legal defense file; the metrics pipeline is the business's nervous system. Both are data problems.

**What You'll Build / Own:**
- PostgreSQL schema for providers, jobs, sessions, rights, payouts, tiers (Phase 1+).
- **Immutable append-only audit log** design: sessions, takedowns, tier changes, payouts — exportable quarterly snapshots into the Evidence Pack (SEP §8). This log answers regulators within 24 hours.
- Analytics pipeline: margin per GPU-hour, session success rate, provider churn, CAC per marketplace side, relay minutes, re-dispatch/fraud rate (the metrics from `business_plan_review.md` §7).
- DPDP deletion-on-request wiring: actual DB erasure paths, not just policy text (Risk L-05).
- Data minimization enforcement: hashed SteamIDs, no title-tracking, ephemeral session data — verified by schema, not promises.
- Warehouse exports (BigQuery/S3 Parquet) once volume justifies it.

**What to Study:**
- **PostgreSQL internals:** *Use The Index, Luke*, MVCC, WAL basics, partitioning audit tables by month.
- **Immutability patterns:** Event sourcing lite, hash-chained logs or just signed monthly exports, WORM storage concepts.
- **Privacy engineering:** DPIA basics, purpose-bound schemas, retention schedules, pseudonymization (hashed IDs).
- **Analytics:** dbt fundamentals or plain SQL marts; product metrics (cohort retention, marketplace liquidity metrics).

**Key Deliverables:**
1. Schema + migrations surviving Phase 1 exit criteria.
2. Audit-log export job feeding counsel's Evidence Pack.
3. Weekly unit-economics dashboard the founders review every Monday.

---

## Role 10 — Site Reliability Engineer (SRE)

**Mission:** Sessions don't die silently, incidents have runbooks, and the control plane survives being attacked.

**What You'll Build / Own:**
- Observability stack: Prometheus metrics, Grafana dashboards, structured logs, alerting with sane thresholds.
- SLOs: matching availability, placement latency, heartbeat freshness, queue health (`PLAN.md` §6 success metrics), session success rate ≥95%.
- Incident response: severity levels, who calls counsel, breach-notification path tying into DPDP timelines, provider/user comms templates **written in advance** (SEP §5).
- DDoS posture review: WAF rules, rate-limit tuning, graceful session continuation during control-plane blips (Risk T-08).
- Production access hygiene: least-privilege, logged production access, founder 2FA everywhere, monthly access audits (Risks T-07, F-03).
- Disaster drills: takedown drill quarterly (L-01), missed-heartbeat floods, payout-system failure simulation.

**What to Study:**
- **Google SRE Book + Workbook** (free at sre.google): SLOs/SLIs, error budgets, incident management.
- **Observability:** OpenTelemetry basics, RED/USE methods, alert fatigue management.
- **Load testing:** k6 or Gatling — model heartbeat storms and matching spikes before they happen.
- **Chaos basics:** Controlled failure injection on staging (kill the orchestrator mid-session; what happens?).
- **IR frameworks:** PagerDuty incident response guides, blameless postmortems.

**Key Deliverables:**
1. Dashboards for every `PLAN.md` §6 metric.
2. Written + rehearsed incident runbook.
3. Quarterly drill log (also feeds the Evidence Pack).

---

# SQUAD B — LEGAL, FINANCE & COMPLIANCE (Roles 11–15)

> **Cost note:** Roles 11–14 are **retained professionals, not employees**. Budget ₹1.5–4 lakh for the initial legal package (SEP §0: "the cheapest insurance you will ever buy") and a modest monthly retainer for the CA.

---

## Role 11 — Technology / Media Lawyer (Retained)

**Mission:** Every activity on the platform maps to a document that permits it. This role *produces those documents*.

**What You'll Do:**
- Draft the SEP §1.2 package: User ToS (hardware-rental framing), Provider Agreement (independent-contractor + indemnity + bond clauses), AUP, Privacy Policy, Takedown & Grievance Policy, Refund Policy.
- Opinion memos: (a) BYOL Steam rental model, (b) marketplace TDS/GST obligations, (c) confirmation the model sits outside real-money-gaming regimes (L-11, SEP §1.5).
- Publisher/indie licensing templates: the §3.2 reusable direct-license contract (30-day termination, territory, rev-share).
- The Steam PC Café inquiry letter and the Valve/publisher/anti-cheat correspondence file.
- Per-jurisdiction compliance review before any SEA expansion (L-13).
- Incident counsel: who you call when a provider sues, a publisher complains, or a regulator writes.

**What to Study / Look For (Hiring Criteria):**
- Bangalore/Delhi/Mumbai firm with **gaming or platform-marketplace practice** — the shortlist action from SEP §10.
- Demonstrated knowledge of: IT Act §79 + Intermediary Guidelines 2021, DPDP Act 2023 + Rules (Nov 2025 notification), Copyright Act §65A, Consumer Protection Act 2019 (e-commerce rules), RBI payment-aggregator norms.
- Ask for one redlined marketplace ToS they've done before — that tells you more than any pitch.

**Key Deliverables:**
1. The complete §1.2 seven-document package.
2. Three standing opinion memos (BYOL, tax, gaming-regime).
3. 24-hour response channel for incidents (stored in Evidence Pack).

---

## Role 12 — Privacy Officer / DPO

**Mission:** DPDP Act compliance is a product deadline (full substantive compliance **May 13, 2027**), not paperwork. One founder owns this now (L-05).

**What You'll Do:**
- Consent architecture: itemized per-purpose consent screens, withdrawal paths, consent records storage.
- Breach-notification runbook: DPBI + user notification paths, severity criteria, timeline drills.
- Data-deletion workflows that really wire into the database (working with Role 9).
- Data inventory + minimization audits: enforce hashed-SteamID-only, no title-level tracking, ephemeral session data.
- Consent Manager framework readiness (operational Nov 13, 2026).
- Vendor DPAs: payment aggregator, KYC vendor, cloud provider.

**What to Study:**
- **DPDP Act 2023 + 2025 Rules** full text (MeitY publications); the phased timeline.
- **Practical privacy ops:** how to run a DSAR (data subject access request) process, breach-notification templates, Record of Processing Activities (RoPA).
- **Certifications:** IAPP CIPP/A or CIPT (not mandatory, but signals seriousness to investors).
- **India-specific guidance:** follow MeitY circulars, Data Protection Board notifications, prominent Indian privacy law firms' alerts.

**Key Deliverables:**
1. Consent records + standalone privacy notice (separate from ToS).
2. Tested breach runbook (tabletop drill logged).
3. Deletion-request pipeline with DB-level proof.

---

## Role 13 — Compliance & Grievance Officer

**Mission:** Own the day-to-day mechanics of IT Act §79 safe harbor — the legal shield that stops you becoming a co-defendant for user behavior (L-04).

**What You'll Do:**
- Publish name + contact as Grievance Officer on the website.
- Run the complaint pipeline: acknowledge within 24 hours, resolve within statutory timelines.
- Maintain the **takedown log**: every complaint, action, timestamp — the exact artifact that proves due diligence.
- Execute "actual knowledge" responses: court order / government notice → disable access expeditiously → preserve records.
- Quarterly takedown drill (paired with L-01 copyright drill).
- Handle consumer complaints (L-07) through the same ≤48h pipeline.

**What to Study:**
- **IT Act §79 + IT (Intermediary Guidelines and Digital Media Ethics Code) Rules, 2021** — especially due-diligence conditions.
- Takedown case studies: how ShareChat/Twitter handled Indian government notices; what's "expeditious" in practice.
- Grievance-handling ops: ticketing discipline, evidence preservation, escalation matrix to counsel.

**Key Deliverables:**
1. Live takedown log with drill entries.
2. Published grievance contact + response-time metrics.
3. Actual-knowledge response runbook.

---

## Role 14 — Chartered Accountant (CA, Retained)

**Mission:** Tax compliance from payout #1 — missed obligations compound monthly (L-09).

**What You'll Do:**
- GST registration and classification confirmation (e-commerce operators register **regardless of turnover**).
- Set up §194-O TDS deduction mechanics with the payments engineer; monthly filings.
- GST invoicing rules for platform fees; GSTR filings calendar.
- TDS certificates for providers; annual reconciliation.
- Advise on bond/deposit structuring (with counsel) so the ₹10–25k T2 security deposit is compliant (SEP §2.5).
- Pre-expansion: SEA tax exposure review.

**What to Study / Look For:**
- CA with **e-commerce or gig-platform clients** (Zomato/Urban Company supplier-side experience is gold).
- Deep familiarity: §194-O, GST on OIDAR/marketplace fees, TCS/TDS interplay.
- Comfort with API-first billing systems — they should read an invoice JSON, not demand Excel.

**Key Deliverables:**
1. Compliance calendar (monthly GST + TDS filing dates).
2. Automated payout-tax pipeline sign-off.
3. Clean annual audit.

---

## Role 15 — Finance / Billing Operations

**Mission:** Know whether the business model is working *weekly*, not at year-end. Kill the "no unit economics" gap from the business review.

**What You'll Do:**
- Track from week 1: gross margin per GPU-hour, take rate (target 20–25%), payment fees (~2%), TDS admin overhead, insurance, support cost.
- Watch the hidden killers: TURN relay minutes (~10–20% of sessions), staging storage, re-dispatch cost on verification failures, fraud loss.
- Enforce the guardrail: provider payout ≤ 70–80% of session price; margin floor ≥60% after infra + fraud.
- Chargeback/fraud ops: representment with audit-log evidence, threshold alerts.
- Runway and pricing models for the Series A story (on top of the §8 Evidence Pack).

**What to Study:**
- **Marketplace unit economics:** a16z marketplace metrics posts, *The Marketplace Playbook* concepts (liquidity, take rate, repeat rate).
- **SaaS/infra margin modeling:** COGS for GPU-hour marketplaces (egress! relay! storage!).
- **FP&A basics in a spreadsheet or Metabase** — you don't need NetSuite at this stage.

**Key Deliverables:**
1. Monday unit-economics dashboard (per GPU-hour margin visibility).
2. Fraud/chargeback weekly report.
3. Board-ready monthly P&L-lite.

---

# SQUAD C — PRODUCT & GROWTH (Roles 16–20)

---

## Role 16 — Indie Game BD / Publisher Relations

**Mission:** Fill the green catalog — 10 signed indie titles before gaming launch, 50 by month 6 (SEP §3.2).

**What You'll Do:**
- Build and work the target list: 30 Indian/SEA indie studios first (SEP §10), contact emails, pitch doc.
- Sell the trade: rev-share per streamed hour + storefront placement + **free cloud QA infrastructure** (the genuinely attractive hook).
- Close using the counsel-approved reusable license template; log every signed PDF into the Evidence Pack + rights DB.
- Feed publisher demand data to counsel for BYOL opt-in outreach (top-20 demanded titles).
- Own the indie dev services stream (cloud QA/test farms, monthly B2B accounts — revenue stream #5).

**What to Study:**
- **BD fundamentals:** structured outbound, pipeline CRM hygiene, negotiation basics (*Never Split the Difference*).
- **Game industry literacy:** how Indian/SEA indies monetize, what Steam rev-share looks like, what "cloud QA" pain actually costs them.
- **IP licensing basics:** territory, windows, termination, trademark usage in catalog display — enough to negotiate before counsel finalizes.

**Key Deliverables:**
1. 10 signed `direct_license` titles pre-launch; 50 by month 6.
2. A repeatable outreach + close playbook.
3. Signed-license archive feeding the rights DB (`rights_basis = direct_license`).

---

## Role 17 — Provider Supply Manager

**Mission:** The marketplace cold-start problem is real (O-01): no providers = no platform. This role recruits and keeps the GPU supply.

**What You'll Do:**
- Recruit from GPU owner communities: mining-rig operators, homelabbers, LAN cafés (the COMPETITOR-ANALYSIS partnership channel) — they already multi-home on Salad/Vast.
- Operate the economics that retain supply: **weekly payouts**, transparent earnings dashboard, competitive rates vs multi-homing alternatives.
- Deliver the §2.6 promises: hardware protection branding (thermal kill-switch), abuse-response promise, availability windows.
- Onboard providers through all 5 gates smoothly (with engineering): KYC friction kills conversion if unmanaged.
- Track provider 30-day retention and effective ₹/hour vs competitors; churn postmortems.

**What to Study:**
- **Marketplace liquidity science:** how Uber/Airbnb seeded supply-side density city by city; seed-your-own-supply tactics.
- **Community ops in India:** Telegram/Discord guild ops, LAN café owner networks, mining-rig communities (they're on X and Discord).
- **Basic crypto-miner economics:** electricity cost per GPU-hour, break-even math — it informs your payout floor.

**Key Deliverables:**
1. 25+ verified providers at T0 before Phase 1 exit.
2. Provider retention dashboard + weekly payout reliability = 100%.
3. A repeatable recruitment funnel (community → KYC → first payout in <7 days).

---

## Role 18 — Growth / Community Manager

**Mission:** Demand is the scarce side of this marketplace. Fill it niche by niche — Blender artists first, ML hobbyists second.

**What You'll Do:**
- Embed in demand communities: BlenderArtists, r/blender, ComfyUI/Stable Diffusion Discords, Indian creator communities.
- Run the Phase 0 validation machine: 25+ demand interviews, landing page + waitlist with concrete pricing ("render 250 frames for ~₹X"), kill/continue gate measurement (≥100 waitlist or ≥10 pre-paid deposits).
- Launch artifacts: pricing pages, comparison content vs AWS/Render Network token friction, tutorial content ("your first render in 15 minutes").
- Work the distribution hack: Blender add-on as a channel (Phase 2 API/access point).
- Feed positioning feedback back to product (outcome UX > machine UX messaging).

**What to Study:**
- **Community-led growth:** *The Cold Start Problem* (Andrew Chen) — mandatory reading for niche-first marketplace seeding.
- **Demand validation discipline:** *The Mom Test* — interviews that don't lie to you.
- **The Blender/3D creator world itself:** actually learn to run a basic render; you cannot sell to artists you don't understand.
- **Growth analytics:** UTM discipline, funnel metrics, waitlist → activation → paid tracking.

**Key Deliverables:**
1. Phase 0 gate metrics delivered on time (waitlist/deposit numbers).
2. 10+ paying compute customers by Phase 1 exit.
3. A living niche-expansion playbook (Blender → ComfyUI → transcode).

---

## Role 19 — Product Manager

**Mission:** Guard the two levers that decide survival: focus (compute first, gaming second) and phase gates (a gate not met = phase doesn't start).

**What You'll Do:**
- Own the roadmap translation: SEP phases → sprint scope → shipped increments; resist scope-smuggling.
- Run user research loops weekly (both sides: renters and providers); 25+ demand interviews in Phase 0.
- Define and police the metrics contract: 95% no-touch completion, ≥40% repeat rate, ≥60% gross margin, <2% fraud.
- Packaging decisions: how compute SKUs (render/fine-tune/transcode) are presented, priced, and limited.
- Scope referee on red-lines: any feature touching SSFN, ID spoofing, credential custody, or DRM workarounds dies in *your* review with a logged decision (SEP §3.5).

**What to Study:**
- **Marketplace PM craft:** Lenny's Newsletter marketplace editions, Reforge marketplace content.
- **Technical depth:** enough systems knowledge to argue with the architect about queue semantics and sandbox boundaries — PM here is technical.
- **Prioritization frameworks used with judgment:** RICE is fine; founders' gut + metrics contract is better at this stage.

**Key Deliverables:**
1. A roadmap the team actually believes in, per phase, with gates honored.
2. Weekly research notes feeding backlog.
3. Decision log (includes red-line rejections — Evidence Pack item #9).

---

## Role 20 — UI/UX Designer

**Mission:** Make the product feel like magic to non-technical creators while making trust signals unmistakable (verified providers, license badges, refund clarity).

**What You'll Do:**
- Design system for `web-client/`: tokens, components, dark mode, motion, empty states.
- Core flows: upload → quote → progress → result (compute); catalog browse → session launch → play (gaming); provider onboarding → earnings (supply).
- Trust UX: how tier badges, reputation scores, and licensed-title markers are displayed without clutter.
- Failure UX: session drops, refund credits, KYC friction — designed so a failure doesn't become a consumer complaint (L-07).
- Marketing surface: landing page, pricing page, indie pitch deck visuals.

**What to Study:**
- **Figma mastery:** components, variants, auto-layout, tokens; dev-handoff discipline.
- **Developer-tool UX:** study Vast.ai, RunPod, Render, Railway, Vercel dashboards — internalize why they're clean.
- **Trust design patterns:** Stripe/Airbnb/UL-style verification signaling, pricing transparency patterns.
- **Basics of WebXR/streaming UI constraints** for the gaming session overlay (latency readouts, reconnect states).

**Key Deliverables:**
1. Shipped design system consumed by the frontend engineer.
2. <15-minute time-to-first-result UX validated with real users.
3. Provider dashboard that supply-side users cite as a retention reason.

---

# Hiring & Phase Map

| Phase | Humans Required | Cumulative Team |
|---|---|---|
| **Phase 0 — Foundation** (Wks 0–6) | Founders (cover Roles 1, 3?, 5, 6, 18, 19) + retained **Lawyer (11)** + retained **CA (14)** + founder-owning **Privacy (12)** + founder-owning **Grievance (13)** | 2–4 |
| **Phase 1 — Compute Revenue** (Mo 2–4) | + **Security & Sandbox Engineer (4)** + **Frontend (8)** + **Provider Supply (17)** + part-time **Finance Ops (15)** | 6–8 |
| **Phase 2 — Green Gaming** (Mo 4–7) | + **Network & Streaming (2)** + **Platform/DevOps (3)** + **Payments Backend (7)** + **Indie BD (16)** + **Designer (20)** | 9–12 |
| **Phase 3 — BYOL AAA** (Mo 7–12) | + **Data Engineer (9)** + **SRE (10)** | 11–14 |
| **Phase 4 — Scale** (Mo 12+) | Full squad + per-country counsel for SEA (Role 11 fork per L-13) | 15–20 |

## Founder-Hat Mapping (Until Hires Land)

| Founder | Hats Worn |
|---|---|
| **Founder 1 (Technical)** | Roles 1 (Architect), 5 (Orchestrator), 6 (Agent), 12 (Privacy), 3 (DevOps, interim) |
| **Founder 2 (Business)** | Roles 19 (PM), 18 (Growth), 17 (Supply), 13 (Grievance), 15 (Finance Ops, with CA) |

## The One Rule

> A role with no name on it is a risk with no control. Map every `RISK-REGISTER.md` row to its owner before Phase 1 — that's the actual hiring plan.

---

*Review per phase alongside the Risk Register and Safe Execution Plan. Update as hiring lands and scopes shift.*
