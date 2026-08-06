# AAA Hosting — Briefing Prompt

**Purpose:** A self-contained prompt to paste into any LLM, advisor, lawyer, or investor conversation to get useful help on the AAA problem. It assumes zero prior context. Copy everything between the rulers.

**Maintenance note:** the "current state" section reflects the repo as of 2026-08-06 (`ae911d6`). Update it before reusing, or the advice you get will be aimed at the wrong codebase.

---

## PROMPT — copy from here

I am building a decentralised peer-to-peer cloud gaming and compute marketplace. I need help solving a specific set of blockers around hosting AAA (paid, big-budget) games. Please read the full context before answering.

### What the product is

A two-sided marketplace with two tracks sharing one infrastructure:

- **Gaming track:** people with idle gaming PCs (RTX-class GPUs) rent them out. Players with weak laptops connect over a low-latency video stream and play games on that remote hardware.
- **Compute track:** the same machines run batch workloads (ML training, Blender renders) when not gaming. This is the revenue floor when gaming demand is low.

Think GeForce NOW, but the hardware is strangers' home PCs instead of a company datacenter. Closest analogues: Vast.ai and io.net (compute, no gaming), GPUnity (P2P gaming, sub-120ms), GeForce NOW and Shadow (centralised gaming).

**Target market:** India first. Rationale: huge population of gamers on weak hardware, price-sensitive, and dense metros mean a provider and player in the same city can hit sub-20ms round-trip. Latency is the whole product — a P2P node 10km away structurally beats a datacenter 800km away.

**Intended moat:** hardware encoder capability (NVENC/QuickSync) as a first-class matching dimension, region-aware latency matching, dual-track supply (gaming + compute on the same fleet), and cache-warmth-aware scheduling.

### Current build state (be accurate about this — it is early)

TypeScript monorepo, Node 20, npm workspaces, Docker Compose.

- `services/orchestrator` — Fastify-style HTTP control plane. Endpoints: `POST /v1/providers/heartbeat`, `POST /v1/match/gaming`, `POST /v1/match/compute`, `POST /v1/jobs`, `GET /v1/jobs/:id`, `GET /health`.
- `services/provider-agent` — daemon on the provider machine, emits heartbeats with capability + telemetry on an interval. Currently emits **synthetic** metrics.
- `packages/contracts` — shared Zod schemas: `ProviderHeartbeat`, `GamingMatchRequest`, `ComputeMatchRequest`, `ComputeJobSubmit`.
- `web-client` — React + Vite + Tailwind landing page.

Matching today is synchronous and score-based. Gaming scoring is a hard filter on `supportsGaming`, exact region match, and `avgRttMs <= maxLatencyMs`; then `100 + encoderBoost(15 if NVENC/QuickSync) - loadPenalty(cpu*0.4 + gpu*0.6) - latencyPenalty(rtt*1.2 + jitter*0.8)`.

**What does not exist yet:** any streaming layer (no WebRTC, no video pipeline), any session lifecycle, any concept of installed/cached game titles, authentication of any kind, persistence (providers and jobs live in in-memory `Map`s and die on restart), payments, and sandboxed execution. The provider agent reports no real telemetry. There are no real users and no real providers.

### The licensing position (already researched — do not re-litigate this)

I researched this thoroughly. Conclusions, with the reasoning:

**Bring Your Own Licence (BYOL) is the model.** The player logs into their own Steam/Epic/Riot account inside the session and plays games they own. The node operator never supplies the licence. This is how GeForce NOW works — NVIDIA owns zero games.

**The operator must never supply the licence.** The Steam Subscriber Agreement forbids renting/leasing/licensing content to others, sharing accounts, commercial use, and using your account to enable others' violations. Four separate clauses. So these designs are permanently off the table: operator's own copy played by a renter; a shared marketplace-owned Steam account holding a game library; offline-mode tricks to skip the ownership check; storing user credentials for background auto-login.

**Under BYOL the legal position is actually strong.** The player uses their own licence for their own personal play, and rents *hardware*, not content. Shadow.tech proves this empirically — they run AAA titles today, are not on Steam's Cloud Play provider whitelist, and never negotiated with Valve, because renting a computer is not licensing a game. The Steam Cloud Play whitelist binds a *catalogue provider* (someone who provisions a library and streams it), not a hardware-rental model.

**One legal path exists for operator-supplied licences if I ever want it:** the Steam PC Café program offers "floating licenses" — buy licences on one account and share them with visitors. It is written for physical venues on a local network, so whether it can cover remote streaming is an open question I intend to ask Valve directly.

**So: the licence is not the blocker.** The blockers are trust, anti-cheat, and unit economics. Please do not spend your answer re-explaining EULA risk — I have that covered. Engage with the four problems below.

### The four actual blockers

**BLOCKER 1 — Credential exposure on untrusted hardware. This is the hardest one.**

Under BYOL, the player must type their Steam password and Steam Guard code into a Windows session running on a stranger's PC that the stranger has kernel-level control over. That operator can keylog the login, dump session tokens from process memory, screen-record the Guard prompt, or persist a stealer that survives the session wipe.

A stolen Steam session token is not one game — it is the entire library, saved payment methods, and CS2/TF2 inventory, which alone can be worth more than the hardware being rented. GeForce NOW and Shadow do not have this problem because they are a single trusted operator running their own datacenter. In a P2P network every session is a new trust decision about an anonymous stranger.

Mitigation ideas I know of, none of which fully solve it: QR-code or OAuth device-flow login so credentials never enter the node; hardware-attested boot; operator KYC plus a slashable financial bond; session-scoped tokens. I need a real threat model here.

**BLOCKER 2 — Kernel anti-cheat, and it punishes my users rather than me.**

Riot Vanguard, EasyAntiCheat, and BattlEye are hostile to virtualised and remote-execution environments and fingerprint hardware. If a player gets HWID-banned from a game because they used my service, that is unreversible, lands on *their* account not mine, and destroys word-of-mouth in exactly the market I am targeting.

This also constrains my free-to-play launch plan, because Valorant and BGMI are free-to-play but heavily anti-cheat protected. **I have not empirically tested this yet.** It is unverified.

**BLOCKER 3 — Disk economics at the edge.**

AAA titles are roughly 60–150GB each. A typical home operator with a 1TB SSD, after Windows and their own games, can keep maybe 6–10 AAA titles warm. GeForce NOW pre-installs ~4,500 titles across petabyte-scale datacenter storage. I have consumer SSDs at the edge.

This means cache-warmth matching is not an optimisation, it is the core scheduling problem — a cold fast node is worse than a warm adequate one. It caps AAA breadth much harder than free-to-play, where India's top titles number in the dozens and are far smaller.

**BLOCKER 4 — Login friction stacks.**

Even with a perfect cache: Steam login → Steam Guard device approval → publisher launcher (Rockstar Social Club / EA App / Ubisoft Connect) → that launcher's own login and device check → game. Steam Guard fires on *every* new machine, and in a P2P network the machine changes every session, so this is permanent friction rather than one-time setup. Worse, one account logging into constantly-rotating unknown machines is the exact behavioural fingerprint of account-selling, so a legitimate user starts looking compromised.

### My current plan

Launch on free-to-play and indie titles first — not for licensing reasons, but because it de-risks the blockers. A throwaway Genshin or BGMI account is a far smaller loss than a full Steam library (shrinks Blocker 1); the catalogue is dozens of small titles rather than thousands of huge ones (removes Blocker 3); and it is one in-game login with no Steam Guard churn and no publisher launcher chain (removes Blocker 4). Blocker 2 remains and is the reason to test anti-cheat before committing.

Then: indie studios via direct written consent, batch compute as the revenue floor, and AAA once Blockers 1 and 2 are actually solved.

### What I want from you

Please engage with the specifics rather than giving generic startup advice. Be direct about what will not work and why — I would rather be told an idea is fatally flawed now than discover it after building it.

1. **Blocker 1 is the one that decides whether AAA is ever reachable. Design a credential-isolation threat model.** Who are the realistic attackers among node operators, what can they actually do with kernel access to their own machine, and which mitigations meaningfully reduce risk versus merely appearing to? Is there any architecture where a player's Steam credentials never become extractable by the node operator — and if not, what is the honest residual risk a user should be told about?
2. **How do I empirically test anti-cheat behaviour cheaply and safely**, without risking a ban on a real account I care about? Which titles are the highest-information tests?
3. **Is the "rent a computer, not a game" framing (the Shadow model) actually defensible for a marketplace of anonymous operators**, or does it break down precisely because I have thousands of untrusted hosts rather than one accountable company? This is the question I am least sure about.
4. **What am I not seeing?** Which blocker have I underestimated, and is there one I have not identified at all?

Constraints worth knowing: I am a solo third-year CS undergraduate in India building this alongside coursework, with near-zero budget. I write all backend code myself and want to understand design decisions rather than receive finished code. Assume I can build things but cannot buy my way past problems.

## PROMPT — copy to here

---

## Notes on using this

- **The "what does not exist yet" paragraph is the most valuable part.** Without it you get advice aimed at a product that already streams video and has users. Keep it honest and keep it current.
- **The licensing section exists to shut down a predictable failure mode:** most models, asked about cloud gaming, will burn the whole answer explaining EULA risk. Pre-empting it forces engagement with the real problems.
- **Question 3 is the highest-value one** and deliberately invites disagreement — it is the load-bearing assumption of the entire AAA path, and the one with the least evidence behind it.
- If you want a shorter version for a quick conversation, keep: what the product is, the four blockers, and question 1. Drop the build state and the licensing section.
