# Peer-to-Peer Cloud Gaming & Compute Marketplace

## Full Product & Engineering Plan

**Document type:** Master roadmap (architecture, phases, legal posture, milestones)  
**Role of this doc:** Single source of truth for what we build, in what order, and why  
**Last aligned decisions:** Cloud gaming first · multi-title legal AAA · hybrid Python + C++ stack · General Compute as Phase 2+  

---

## 1. Vision

Build a **decentralized marketplace for computing resources** — a pragmatic “Peer-to-Peer AWS” — where people with idle high-end hardware (Providers) sell capacity to people who need it (Consumers).

### 1.1 Core value proposition

| Actor | Value |
|--------|--------|
| **Consumer** | Play AAA games (and later run heavy compute) without owning a $1,500–$3,000 GPU rig |
| **Provider** | Monetize idle hardware with clear safety limits and isolation |
| **Platform** | Match supply/demand, meter usage, settle payments, enforce policy — without running the heavy workloads |

### 1.2 Pragmatic hybrid model

We do **not** put all execution on our servers (too expensive, high latency).  
We do **not** go fully trustless/blockchain-first (too slow to ship, weak UX for gaming).

```
┌──────────────────────────────────────────────────────────┐
│  CENTRAL ORCHESTRATOR (our AWS backend)                  │
│  Auth · matching · catalog · sessions · metrics · pay    │
└────────────────────────────┬─────────────────────────────┘
                             │ control plane (HTTPS / WSS)
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
   Provider Agent      Provider Agent      Provider Agent
         │                   │                   │
         ▼                   ▼                   ▼
   Stream Host (C++)   Stream Host (C++)   Stream Host (C++)
   Game on Provider    Game on Provider    Game on Provider
         │                   │                   │
         └──────── P2P / direct media (WebRTC) ──┘
                             │
                             ▼
                      Consumer Client
```

- **Centralized:** identity, catalog, matching, session lifecycle, billing, trust & safety  
- **Decentralized:** actual pixels, encode, decode, and (later) batch compute execution  

---

## 2. Product surfaces

### 2.1 Vertical A — Cloud Gaming (PRIMARY / first to market)

**Goal:** Consumers play **legally supported multi-title AAA games** on a Provider’s machine via ultra-low-latency streaming.

**Characteristics:**

- Real-time interactive session  
- WebRTC (P2P preferred; relay fallback when NAT fails)  
- Hardware encode (NVENC / AMF / QuickSync)  
- SRTP encryption on media  
- Input pipeline with OS-level chord sanitization  
- Window-scoped capture (game only, not full desktop by default)  

**Catalog posture:** Multi-title from day one — games are **data (launch profiles)**, not hard-coded product modes.

### 2.2 Vertical B — General Compute (SECONDARY / after gaming spine)

**Goal:** Batch jobs (Blender, encoding, ML training, etc.) on Provider GPUs/CPUs.

**Characteristics:**

- High throughput over low latency  
- Secure file transfer (TLS)  
- Docker isolation  
- VRAM/GPU allocation and hard resource caps  
- Volatile workspace wiped on completion  

### 2.3 Why gaming first

| Reason | Detail |
|--------|--------|
| Clear consumer story | “Play AAA on any device” is easier to demo and market than “rent a GPU” |
| GTM / hype | Position for GTA 6–era demand without depending on a single unreleased title |
| Shared spine | Orchestrator + agent + session lifecycle transfer cleanly to Compute later |
| Monetization intuition | Hourly/session pricing for streams is well understood |

**Note on GTA 6:** Console hype ≠ PC Provider supply. PC release is expected later than console. We ship multi-title streaming **now** on currently available AAA titles; GTA 6 PC becomes a **catalog entry + launch profile** when license posture and install base allow — not a rewrite.

---

## 3. Legal & trust model (non-negotiable)

### 3.1 Operating model: BYOL + technical allowlist

We sell **stream / compute time**, not game copies.

| Rule | Implementation |
|------|----------------|
| **Bring Your Own License (BYOL)** | Provider (and Consumer when required by publisher) holds a legitimate store license |
| **Allowlist only** | Only titles with defined legal status + technical profile appear in catalog |
| **No piracy path** | Agent rejects cracked/unsigned installs; verify store install markers |
| **Honest status** | `supported` / `limited` / `unsupported` per title (anti-cheat, multiplayer, ToS) |
| **Future partnerships** | Publisher / store cloud-allowlist deals (GeForce Now–style) for restricted titles |

### 3.2 What we do not build

- Grey-market “shared account farm” as a product feature  
- Shipping game binaries ourselves without rights  
- Claiming every Steam game is legal to stream commercially  

### 3.3 Per-title legal status fields (catalog)

```text
legal_status: byol_allowed | partner_only | blocked | under_review
stores: steam | epic | rockstar | other
multiplayer: full | limited | single_player_only
notes: human-readable risk / QA notes
```

---

## 4. Security architecture

### 4.1 Provider protection — Gaming

| Control | Purpose |
|---------|---------|
| Window-scoped capture | Consumer sees game, not Provider desktop/files |
| Input sanitization | Block OS chords (Alt+Tab, Win, Ctrl+Alt+Del patterns, etc.) |
| Process allowlist | Only approved launcher + game process trees |
| Session isolation | Per-session temp profiles/dirs where feasible; cleanup on end |
| Hardware caps | Agent enforces GPU temp / power / utilization kill switches (e.g. ≥ 85°C policy) |
| Agent least privilege | Run with minimum rights needed; no silent admin escalation |

### 4.2 Provider protection — General Compute (later)

| Control | Purpose |
|---------|---------|
| Docker (or stronger) isolation | Malicious jobs cannot freely touch host FS |
| Resource limits | CPU, RAM, GPU, disk, network quotas |
| No host mounts by default | Only ephemeral workspace volume |
| Auto-wipe | Destroy workspace on success/fail/timeout |
| Image allowlist | Only approved base images / job images |

### 4.3 Consumer protection

| Control | Purpose |
|---------|---------|
| TLS for control plane & file transfer | Confidentiality in transit |
| SRTP for media | Encrypted game stream / audio |
| Volatile storage on Provider | No long-term retention of Consumer artifacts |
| Wipe-on-complete | Policy-enforced cleanup |
| Session tokens | Short-lived credentials for P2P signaling |

### 4.4 Platform protection

- Provider reputation / fraud signals  
- Rate limits, abuse detection  
- Signed agent builds and update channel  
- Audit logs for session start/stop, game launched, wipe result  

---

## 5. Tech stack (locked direction)

### 5.1 Hybrid language strategy

| Layer | Stack | Rationale |
|-------|--------|-----------|
| **Orchestrator** | Python, AWS, PostgreSQL | Fast iteration for APIs, matching, catalog, billing |
| **Provider Agent (control plane)** | Python (v0); optional Go later for single binary | Heartbeat, library scan, launch/stop, policy |
| **Stream Host (media plane)** | C++ and/or battle-tested C++-backed stack | Capture, NVENC/AMF/QSV, WebRTC, input |
| **Virtualization (Compute)** | Docker | Isolation for batch jobs |
| **Consumer client (v0)** | Browser WebRTC | Fastest validation |
| **Consumer client (later)** | Native desktop / mobile | Better decode, gamepad, UX |

**Principle:** C++ where latency is felt (pixels/input). Python where product changes weekly (marketplace).

### 5.2 Reference architecture — Gaming session

```
Consumer Client                    Orchestrator                     Provider
     │                                  │                              │
     │  POST /sessions {game_id}        │                              │
     │─────────────────────────────────►│                              │
     │                                  │  match Provider (GPU+owns)   │
     │                                  │─────────────────────────────►│
     │                                  │  assign session              │
     │◄──── signaling endpoints ────────│◄──── accept ─────────────────│
     │                                  │                              │
     │◄══════════ WebRTC media (P2P or relay) ═══════════════════════►│
     │   video/audio ──► decode                                        │
     │   input ────────► sanitize ──► inject                           │
     │                                  │                              │
     │  end session                     │  stop game · wipe · report   │
     │─────────────────────────────────►│─────────────────────────────►│
```

### 5.3 Game as configuration (not code forks)

Example catalog entry:

```json
{
  "game_id": "cyberpunk_2077",
  "title": "Cyberpunk 2077",
  "legal_status": "byol_allowed",
  "stores": ["steam", "epic"],
  "min_vram_mb": 8192,
  "min_ram_mb": 16384,
  "launch": {
    "type": "steam",
    "app_id": "1091500"
  },
  "capture": {
    "mode": "window",
    "title_regex": ".*Cyberpunk.*"
  },
  "input": {
    "block_os_chords": true,
    "allow_gamepad": true
  },
  "session": {
    "max_minutes_default": 240,
    "idle_timeout_minutes": 15
  },
  "support_tier": "supported",
  "notes": "v0 focus: single-player; multiplayer TBD"
}
```

New AAA titles ship as **catalog + QA**, not platform rewrites.

---

## 6. Domain model (core entities)

| Entity | Description |
|--------|-------------|
| **User** | Account; roles Consumer and/or Provider |
| **ProviderNode** | Registered machine + agent identity + capabilities |
| **HardwareSnapshot** | GPU model, VRAM, driver, CPU, RAM, temps, free capacity |
| **Game** | Catalog entry (metadata, legal, launch, capture) |
| **ProviderGameInstall** | Detected install of allowlisted game on a node |
| **Session** | Gaming (or later Job) lifecycle record |
| **MatchOffer** | Assignment of Consumer request → ProviderNode |
| **MeteringEvent** | Time slices, bitrate, disconnects (for billing) |
| **Payment / Credit** | Later: wallet, payouts, holds |
| **Job** (Compute) | Later: batch work unit, artifact URIs, exit status |

### 6.1 Session states (Gaming)

```text
requested → matching → assigned → launching → signaling → live → ending → completed
                                              ↘ failed
                                              ↘ cancelled
```

### 6.2 Agent states

```text
offline → registering → online_idle → reserved → streaming → draining → online_idle
                                                      ↘ error_cooldown
```

---

## 7. Phase roadmap overview

| Phase | Name | Primary outcome |
|-------|------|-----------------|
| **0** | Foundations | Repo, standards, contracts, environments |
| **1** | Control plane spine | Orchestrator + Agent can register, heartbeat, list capacity |
| **2** | Multi-title catalog | Games as data; library detection; match on “owns game X” |
| **3** | Streaming MVP | One end-to-end playable session (allowlisted titles) |
| **4** | Hardening & security | Capture policy, input sanitization, caps, wipe, observability |
| **5** | Closed beta marketplace | Multi-Provider, multi-Consumer, basic UX, waitlist quality |
| **6** | Metering & payments | Credits, usage, Provider payouts (MVP) |
| **7** | Scale & reliability | NAT/relay, multi-region, QoS, anti-fraud |
| **8** | General Compute vertical | Docker jobs, file I/O, GPU allocation |
| **9** | Growth & partnerships | Publisher deals, mobile clients, GTA 6 PC readiness |
| **10** | Platform maturity | SLAs, enterprise, advanced scheduling, global supply |

Phases are **sequential for the critical path**, but some workstreams (docs, legal review of titles, branding) can run in parallel.

---

## 8. Phase 0 — Foundations

### 8.1 Goal

Create a clean base so every later phase builds on the same contracts and quality bar.

### 8.2 Scope

- Monorepo (or polyrepo with clear boundaries) layout:
  - `orchestrator/` — Python API service  
  - `agent/` — Provider control-plane daemon  
  - `stream-host/` — C++ / media plane (or integration wrapper)  
  - `catalog/` — game definitions (YAML/JSON) + validation  
  - `clients/web/` — Consumer web client  
  - `docs/` — ADRs, runbooks, this plan  
  - `infra/` — local compose, later IaC  
- Engineering standards: lint, format, CI skeleton, commit conventions  
- Environment matrix: local dev, staging, production (AWS)  
- Secrets handling pattern (never commit keys)  
- ADR-001: hybrid architecture + language split  
- ADR-002: BYOL + allowlist legal model  

### 8.3 Deliverables

- [ ] Repo skeleton with README per component  
- [ ] OpenAPI / protobuf draft for control APIs  
- [ ] Local Postgres via Docker Compose  
- [ ] CI: lint + unit test hooks  

### 8.4 Exit criteria

Any engineer can clone, run orchestrator + empty agent against local Postgres, and hit health endpoints.

### 8.5 Explicitly out of scope

Streaming, payments, Docker compute, production AWS scale-out.

---

## 9. Phase 1 — Control plane spine

### 9.1 Goal

Prove the **marketplace nervous system**: Providers appear online with hardware facts; Orchestrator tracks them.

### 9.2 Scope

**Orchestrator**

- User auth (API keys or JWT for v0; OAuth later)  
- `POST /providers/register`  
- `POST /providers/heartbeat`  
- `GET /providers` (internal/admin)  
- PostgreSQL models: User, ProviderNode, HardwareSnapshot  
- Basic auth middleware  

**Agent**

- Config: orchestrator URL, node credentials  
- Startup registration  
- Periodic heartbeat (GPU name, VRAM, driver, CPU, RAM, load, optional temp)  
- Graceful offline / last-seen TTL (orchestrator marks stale nodes offline)  

### 9.3 Deliverables

- [ ] Working register + heartbeat loop  
- [ ] DB migrations  
- [ ] Integration test: agent appears online within N seconds  

### 9.4 Exit criteria

A physical or VM Provider stays `online` in orchestrator while agent runs; goes `offline` after missed heartbeats.

### 9.5 Risks & mitigations

| Risk | Mitigation |
|------|------------|
| GPU telemetry inconsistent across vendors | Start with NVIDIA + nvidia-smi; abstract interface for AMD/Intel later |
| Clock skew / zombie nodes | Heartbeat TTL + explicit shutdown webhook |

---

## 10. Phase 2 — Multi-title catalog & library awareness

### 10.1 Goal

Make the platform **game-agnostic**: match is “who can host *this* allowlisted title,” not “run arbitrary exe.”

### 10.2 Scope

**Catalog service / module**

- Store game definitions (files in repo for v0; admin CMS later)  
- Validate schema (min VRAM, launch type, legal_status)  
- Public `GET /games` (only non-blocked)  
- Internal game detail for matching  

**Agent library detection (Steam first)**

- Detect Steam install path  
- Resolve allowlisted `app_id`s present on disk  
- Report `ProviderGameInstall[]` on heartbeat or dedicated sync  
- Refuse non-allowlisted / unverified installs for launch  

**Matching precursor**

- Query: Providers online + free + meet min hardware + have `game_id` installed  

### 10.3 Deliverables

- [ ] Initial catalog: **3–5** QA’d AAA titles (single-player friendly preferred)  
- [ ] Steam detection MVP  
- [ ] API: list games; list Providers capable of game X  

### 10.4 Exit criteria

Given game_id, orchestrator returns only Providers that are online, capable, and have a verified install.

### 10.5 Explicitly out of scope

Epic/Rockstar full detection, perfect DRM edge cases, automatic updates of games.

### 10.6 Parallel workstream

Legal/tech review pipeline for adding titles (checklist: ToS notes, anti-cheat, launch reliability, capture title regex).

---

## 11. Phase 3 — Streaming MVP (end-to-end)

### 11.1 Goal

**First playable vertical slice:** Consumer requests allowlisted game → matched Provider → game launches → WebRTC stream + input → session ends cleanly.

### 11.2 Scope

**Orchestrator session API**

- `POST /sessions` `{ game_id }`  
- Match algorithm v0: first fit / random among capable idle Providers  
- Session state machine  
- Signaling relay endpoints (SDP/ICE exchange via orchestrator or dedicated signal service)  
- TURN/STUN configuration distribution  

**Stream host (C++ path)**

- Prefer integrate/adapt proven host (e.g. Sunshine-class architecture) before greenfield everything  
- Hardware encode path (NVENC first)  
- WebRTC send of video/audio  
- Receive input channel  

**Agent**

- On assign: reserve node → invoke stream host + launch profile → report `launching` / `live` / `failed`  
- On end: stop stream host, stop game, basic cleanup, release node  

**Web client**

- Login / API token  
- Game picker (catalog)  
- Session view: video element + input capture  
- Basic stats overlay (optional): RTT, fps, bitrate  

### 11.3 Quality targets (MVP, not production SLA)

| Metric | MVP target |
|--------|------------|
| Same-region LAN / good network | Playable interactive feel |
| Encode | 1080p30 or 1080p60 where GPU allows |
| Start time | Game launch + stream &lt; ~60–120s depending on title |
| Failure | Clear error if no Provider / launch fail |

### 11.4 Deliverables

- [ ] E2E demo script for ≥ 1 allowlisted title  
- [ ] Session lifecycle persisted end-to-end  
- [ ] P2P WebRTC success path documented; known NAT failure modes listed  

### 11.5 Exit criteria

Internal demo: Consumer in browser plays an allowlisted AAA title running on a remote Provider machine with keyboard/mouse (gamepad nice-to-have).

### 11.6 Risks & mitigations

| Risk | Mitigation |
|------|------------|
| WebRTC NAT failure | STUN + managed TURN relay (accept bandwidth cost for reliability) |
| Capture wrong window | Title regex + process attach; fallback fullscreen only if policy allows |
| Long game boot | Pre-warm policies later; show “launching” UX honestly |
| Greenfield C++ delay | Start from existing stream host; wrap with our agent |

---

## 12. Phase 4 — Hardening & security

### 12.1 Goal

Make the MVP **safe enough for non-employees** on trusted beta hardware.

### 12.2 Scope

**Gaming security**

- Enforce window-only capture for support_tier ≥ supported  
- Input sanitization v1: block dangerous OS chords; optional sticky-key traps  
- Cursor/clip policy  
- Disable Consumer access to Provider host shell  

**Agent safety**

- GPU thermal / power cap → auto-end session + cooldown  
- Max session duration  
- Idle timeout  
- Crash recovery: detect dead stream host / game; fail session  

**Cleanup**

- Session-end wipe checklist: temp dirs, optional secondary profiles, clipboard  
- Report wipe success/failure to orchestrator  

**Observability**

- Structured logs (session_id correlation)  
- Metrics: session success rate, time-to-live, disconnect reasons  
- Alerts on agent crash loops  

### 12.3 Deliverables

- [ ] Security checklist signed off for closed beta  
- [ ] Kill-switch policies configurable per node  
- [ ] Runbook: compromised session / abusive Consumer  

### 12.4 Exit criteria

Security review of Provider attack surface (malicious Consumer) has documented residual risks and accepted mitigations.

---

## 13. Phase 5 — Closed beta marketplace

### 13.1 Goal

Real multi-user marketplace behavior with limited supply/demand.

### 13.2 Scope

**Product**

- Consumer onboarding (invite-only)  
- Provider onboarding (KYC-lite later; for beta: trusted Operators)  
- Game catalog UX with support tiers  
- Session history for both sides  
- Basic ratings / “session quality” feedback  

**Matching v1**

- Filters: VRAM, GPU tier, region/latency hint, price (if set), installed game  
- Queue when no capacity  
- Soft affinity: prefer lower RTT  

**Reliability**

- Automatic re-match on launch failure (1–2 attempts)  
- Better ICE / TURN defaults  
- Agent auto-update channel (signed)  

### 13.3 Deliverables

- [ ] Beta with N Providers and M Consumers (targets set at kickoff; e.g. 10 / 50)  
- [ ] Weekly quality dashboard  
- [ ] Title expansion process (add 5–15 more allowlisted games)  

### 13.4 Exit criteria

Unattended sessions complete successfully at an agreed success rate; Providers can leave agent running for days without manual babysitting.

---

## 14. Phase 6 — Metering & payments

### 14.1 Goal

Money follows usage without blocking core tech.

### 14.2 Scope

**Metering**

- Billable seconds while `live`  
- Optional quality adjustments later (not v1)  
- Provider earnings ledger  

**Payments MVP**

- Consumer credits (Stripe or similar)  
- Hold/capture per session or post-paid wallet debit  
- Provider payout threshold + manual or automated payouts  
- Dispute freeze flag on session  

**Policy**

- Minimum session charge  
- Cancellation windows  
- No-show Provider penalties (soft at first)  

### 14.3 Deliverables

- [ ] Ledger accurate vs session timestamps  
- [ ] Consumer can buy credits and start a paid session  
- [ ] Provider balance visible  

### 14.4 Exit criteria

Finance-critical path audited for double-charge and unpaid usage gaps.

### 14.5 Explicitly out of scope (this phase)

Complex auctions, dynamic surge pricing, crypto settlement.

---

## 15. Phase 7 — Scale & reliability

### 15.1 Goal

Survive growth beyond a single region and hobby NAT conditions.

### 15.2 Scope

**Networking**

- Regional orchestrator or regional match groups  
- TURN capacity planning  
- Optional SFU later only if product requires (default remains P2P)  

**QoS**

- Adaptive bitrate  
- Congestion feedback  
- Client network pre-check before match  

**Platform**

- Multi-AZ orchestrator  
- DB backups, migrations discipline  
- Rate limits, WAF, DDoS posture  
- Fraud: multi-account, session farming, chargebacks  

**Agent fleet**

- Gradual rollouts  
- Crash telemetry  
- Driver compatibility matrix  

### 15.3 Deliverables

- [ ] Capacity plan for 10× beta load  
- [ ] SLO draft: session start success, disconnect rate  
- [ ] Incident response runbook  

### 15.4 Exit criteria

Load-tested control plane; documented media cost model (especially TURN relay %).

---

## 16. Phase 8 — General Compute vertical

### 16.1 Goal

Reuse the spine for **task-based work** without breaking gaming.

### 16.2 Scope

**New domain: Job**

- Submit job (image, command, input artifacts, GPU requirements)  
- Match Provider with free GPU/CPU  
- Agent pulls inputs over TLS  
- Run inside **Docker** with resource limits  
- Stream logs (optional)  
- Upload outputs  
- Wipe workspace  
- Meter by GPU-seconds / wall time  

**Agent extensions**

- Docker runtime dependency  
- GPU device mapping policy  
- Concurrent gaming vs compute scheduling rules (default: mutual exclusion on same GPU)  

**Orchestrator**

- Job state machine parallel to Session  
- Artifact storage (S3) for inputs/outputs  
- Separate pricing  

### 16.3 Deliverables

- [ ] Demo jobs: e.g. Blender still, ffmpeg transcode, small CUDA sample  
- [ ] Hard fail if container escapes mounts (test suite)  
- [ ] Wipe verification tests  

### 16.4 Exit criteria

Untrusted sample job cannot read host home directory; outputs only via declared artifact path.

### 16.5 Why after gaming

Compute needs the same node identity, heartbeat, matching, metering, and trust systems — already proven under Session pressure.

---

## 17. Phase 9 — Growth, GTA 6 PC readiness & partnerships

### 17.1 Goal

Convert cultural moments and publisher relationships into supply/demand.

### 17.2 Scope

**GTM**

- Position as multi-title P2P cloud gaming (not a single-game client)  
- Waitlist and Provider recruitment around major PC releases  
- Content: “play on any laptop; hardware stays yours as Provider”  

**GTA 6 PC (when available)**

- Legal review against Rockstar / platform ToS  
- Technical profile: launch, anti-cheat, capture, performance tier  
- Catalog entry only if `legal_status` allows  
- Capacity planning: expect demand spike; may need Provider incentives  

**Partnerships**

- Store / publisher conversations for cloud-allowed titles  
- OEM or café Provider fleets (optional)  

**Clients**

- Native Windows client (better input/gamepad)  
- Android / iOS thin clients if latency acceptable  

### 17.3 Deliverables

- [ ] Public marketing site aligned with legal claims  
- [ ] Title onboarding playbook for “mega-release” weeks  
- [ ] Partnership one-pager  

### 17.4 Exit criteria

Playbook exists to add a major new AAA title in days (QA + config), not months (re-architecture).

---

## 18. Phase 10 — Platform maturity

### 18.1 Goal

Operate as durable infrastructure, not a prototype network.

### 18.2 Scope

- Advanced scheduling (preemption, reservations, Provider calendars)  
- Reputation, insurance-like Provider guarantees  
- Enterprise / studio bulk compute & private Provider pools  
- Stronger sandboxing (gVisor/Firecracker research for compute)  
- Multi-cloud orchestrator DR  
- Compliance reviews (payments, data retention, regional law)  
- Open Provider economics dashboard  

### 18.3 Exit criteria

Defined SLOs with error budgets; on-call rotation; financial reconciliation automation.

---

## 19. Cross-cutting workstreams (all phases)

| Workstream | Activities |
|------------|------------|
| **Legal** | Title reviews, ToS of Steam/Epic/Rockstar, privacy policy, Provider agreement |
| **Security** | Threat models (malicious Consumer, malicious Provider, malicious job) |
| **QA** | Per-title launch/capture matrix; regression before catalog publish |
| **Design/UX** | Session UX, Provider dashboard, error honesty |
| **Data** | Metrics taxonomy; privacy-minimized telemetry |
| **Support** | Runbooks, status page (later), dispute process |

---

## 20. Suggested milestone timeline (indicative)

> Adjust to team size. Assumes small founding team (2–4 eng) focused full-time.

| Milestone | Approx. window | Phase mapping |
|-----------|----------------|---------------|
| M0 Repo + contracts live | Weeks 1–2 | Phase 0 |
| M1 Agent online in orchestrator | Weeks 2–4 | Phase 1 |
| M2 Catalog + Steam detect + match query | Weeks 4–6 | Phase 2 |
| M3 First playable E2E stream | Weeks 6–12 | Phase 3 |
| M4 Security hardening for external beta | Weeks 12–16 | Phase 4 |
| M5 Closed beta running | Weeks 16–24 | Phase 5 |
| M6 Paid sessions MVP | Weeks 24–32 | Phase 6 |
| M7 Scale pass + multi-region story | Months 8–12 | Phase 7 |
| M8 Compute vertical MVP | Months 10–14 | Phase 8 |
| M9 Growth / major-title readiness | Ongoing from beta | Phase 9 |
| M10 Maturity | Year 2+ | Phase 10 |

Streaming MVP duration is the highest variance item (media stack integration).

---

## 21. Team focus by phase (founding stage)

| Phase | Who leans in |
|-------|----------------|
| 0–2 | Full-stack / backend heavy |
| 3–4 | Systems + media (C++/WebRTC) + backend |
| 5–6 | Product UX + backend + ops |
| 7 | Infra / SRE mindset |
| 8 | Containers + backend |
| 9 | BD / legal / growth + eng support |
| 10 | Entire org |

Hire priority after founders: **media/streaming engineer**, then **infra**, then **growth eng**.

---

## 22. Success metrics

### 22.1 Product (Gaming)

- Session start success rate  
- Median time-to-first-frame  
- Median RTT / gameplay subjective score  
- % sessions using P2P vs TURN  
- Catalog size × % sessions per title  

### 22.2 Marketplace

- Active Providers (7-day)  
- Supply hours online  
- Utilization %  
- Consumer retention D1/D7  
- Take rate and gross marketplace volume (post payments)  

### 22.3 Safety

- Provider-reported incidents  
- Wipe failure rate  
- Thermal kill events  
- Chargebacks / disputes  

### 22.4 Compute (later)

- Job success rate  
- Queue wait time  
- GPU-hour volume  

---

## 23. Risk register (top)

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Underestimate WebRTC/NAT difficulty | High | High | TURN early; reuse mature stream host |
| Publisher ToS blocks key titles | High | Medium | Allowlist honesty; pursue partners; multi-title portfolio |
| Anti-cheat bans streaming setups | High | Medium | Prefer single-player first; status=limited |
| GTA 6 PC later than expected | Medium | High | Don’t couple launch to one title |
| Malicious Consumers abuse Providers | High | Medium | Capture/input policy, sessions caps, reputation |
| Malicious Providers abuse Consumers | High | Medium | Encryption, wipe, reputation, optional attestation later |
| All-C++ rewrite temptation | Medium | Medium | Enforce hybrid stack ADRs |
| TURN bandwidth costs | Medium | High | Prefer P2P; price relay; regional matching |
| Provider supply cold start | High | High | Seed Providers (founders, friends, cafés, incentives) |

---

## 24. Decision log (locked for this plan)

| Decision | Choice |
|----------|--------|
| Architecture | Pragmatic hybrid (central orchestrator + decentralized execution) |
| First vertical | Cloud gaming |
| Game support | Multi-title, legally constrained allowlist (BYOL) |
| Second vertical | General Compute (Docker), after gaming spine |
| Orchestrator language | Python + PostgreSQL + AWS |
| Agent control plane | Python first |
| Media plane | C++ / proven C++-backed stream host |
| Consumer v0 client | Browser WebRTC |
| Payments | After playable beta (Phase 6) |
| Blockchain | Not required for v0–v1 |

---

## 25. Immediate next actions (start of Phase 0)

1. Create monorepo structure (`orchestrator`, `agent`, `stream-host`, `catalog`, `clients/web`, `docs`, `infra`).  
2. Write ADR-001 (hybrid architecture) and ADR-002 (BYOL allowlist).  
3. Draft OpenAPI for: auth, providers, heartbeats, games, sessions.  
4. Stand up local Postgres + orchestrator health + agent heartbeat proof.  
5. Pick initial **3–5** allowlisted AAA titles for Phase 2–3 QA.  
6. Spike stream-host options (build vs integrate) with a 1-week timebox; decide before Phase 3 deep work.  

---

## 26. Document maintenance

- Update this `plan.md` when a phase exit criterion changes or a locked decision flips.  
- Prefer **ADRs** for architectural decisions; keep this file as the roadmap narrative.  
- Phase exit checkboxes can move to GitHub Projects / Linear; keep definitions of done here.  

---

## 27. One-line summary

**Build a multi-title, legally allowlisted P2P cloud gaming marketplace on a hybrid control/media plane; harden it into a paid beta; then extend the same spine to Dockerized general compute — without betting the company on a single unreleased game or an all-C++ rewrite.**
