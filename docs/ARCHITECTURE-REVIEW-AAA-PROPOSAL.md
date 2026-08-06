# Architecture Review — "Family Sharing DMZ / Hardware Spoofing / Title Sharding"

**Date:** 2026-08-06
**Reviewing:** four-part AAA-enablement proposal
**Verdict:** 1 genuinely good idea, 1 good idea with a broken technical assumption, 2 that escalate liability from civil to criminal.

---

## Scorecard

| # | Proposal | Verdict |
|---|---|---|
| 3 | Title Sharding (orchestrator-dictated storage, demand-driven pre-provisioning, strict routing) | **Adopt the core.** One fatal technical assumption to fix; kill the BitTorrent layer. |
| 1 | Family Sharing DMZ (burner account, blast-radius reduction) | **Right instinct, wrong mechanism.** Creates a new weaponisable attack. Better native option exists. |
| 4 | Anti-cheat segregation | **Directionally right, one factual error.** Needs a verified per-title allowlist, not a category heuristic. |
| 2 | SMBIOS/CPUID/MAC spoofing + ssfn injection | **Do not build.** This is the line between contract breach and criminal offence. |

---

## 1. Title Sharding — the good idea

The core is right and I'd adopt it:

- Providers allocate a dedicated marketplace partition (250–500GB) rather than choosing their own catalogue.
- The orchestrator drives provisioning from **local city demand**, not provider preference.
- Matching routes strictly to warm shards.

This converts cache warmth from hope into managed inventory, and it fits the existing `matching.ts` model cleanly — a shard set becomes a hard filter alongside `region`, exactly like `supportsGaming` is today.

### The broken assumption: SteamCMD anonymous login

> "instructs 5 idle compute nodes in Pune to silently download GTA V in the background using SteamCMD using anonymous login"

**This does not work.** `steamcmd +login anonymous` only reaches apps explicitly flagged for anonymous access — in practice dedicated-server packages (CS2 server appid 740, TF2 server 232250, etc.). Paid game depots are licence-gated. GTA V, Cyberpunk, and RDR2 cannot be pulled anonymously. `app_update` on an unowned appid fails with an access/licence error.

To pre-download a paid title with SteamCMD, an account that **owns** it must be logged in. That leaves only three options, and all three are doors we already closed:

1. The provider owns it → provider-supplied licence → SSA rental clause.
2. The marketplace owns it on a shared account → the single most dangerous idea from earlier sessions.
3. The user's credentials sit on the node before the session → the credential problem, but worse, because now it is unattended.

### This is actually a better statement of Blocker 3 than I gave you

I framed Blocker 3 as disk economics. The disk is the *visible* constraint. The structural one is:

> **A paid game cannot be cached without a licence present at cache time.**

Pre-caching and BYOL are in direct tension for paid titles. That tension, not SSD capacity, is what caps AAA at the edge. Worth putting in AAA-BLOCKERS.md as the corrected version.

**What survives:** Title Sharding works perfectly for content where the licence is not per-user at download time — F2P clients, indie titles under direct written agreement, DRM-free GOG builds you are licensed to stage, and your own compute-track container images. Build it there first. The architecture is right, the catalogue is narrower than you assumed.

**Legitimate partial fix for paid titles:** scheduled warming under the user's own session — the user's booking starts a warming window early, the download runs under *their* credentials with them present, they pay a small reservation fee for provider bandwidth. That is your existing SESSION-FLOW idea, and it is the only version that keeps the licence chain intact.

### Kill the BitTorrent layer

> "Node B can pull the game files from Node A at near-gigabit local speeds"

This is the one item in the whole proposal that is straightforwardly **copyright infringement**, not EULA breach. Node A transmitting game binaries to Node B is unauthorised reproduction and distribution of a copyrighted work. The receiving user owning a licence does not authorise Node A to distribute it — that is not what a licence grants. This is the Napster fact pattern with your orchestrator as the index.

**Legitimate alternative worth investigating: LAN-cache-style transparent CDN caching.** A per-city caching node that caches Steam's *encrypted depot chunks* while the manifest and licence flow still go to Valve per-account. The user's client still authenticates and still gets keys from Steam; you only spare the WAN transfer. This is common at LAN events and is a materially different legal object from peer-to-peer file distribution, because the entitlement check is never bypassed.

I have not verified Valve's current position on third-party depot caching — treat it as a promising lead, not a cleared path, and it is a good concrete question for the Valve email.

---

## 2. Family Sharing DMZ — right instinct, wrong mechanism

The instinct is correct and it is the right *category* of solution: if you cannot prevent theft, make the stolen thing worthless. Blast-radius reduction is exactly how to think about Blocker 1.

But the specific mechanism has a hole that inverts it.

### Verified from Valve's Steam Families FAQ

Direct quote from help.steampowered.com:

> "Your Steam Family privileges may be revoked and **your account may also be VAC banned** if a member of your Steam Family playing a game from you cheats or commits fraud."

You anticipated this and proposed to mitigate it by restricting the burner from launching multiplayer titles on your platform.

**That mitigation does not hold, because the attacker is not on your platform.** A malicious provider steals the burner session token, takes it to their own machine, launches a VAC-protected shared title, and cheats deliberately. The VAC ban propagates up to the victim's main account. You cannot restrict what a thief does with a stolen token off your network.

So the DMZ does not just fail to protect the main account — it **builds a channel from a low-value stolen credential to a permanent ban on the high-value account.** Pre-DMZ, a stolen burner token was worthless. Post-DMZ, it is a weapon aimed at the thing you were protecting. That is a net increase in risk, and it is cheap to execute and attributable to nobody.

### Three more verified constraints

**Family Sharing exclusions hit your exact target list.** Games that cannot be shared include:

> "Games that require an additional third-party key, account, or a subscription in order to play"

That excludes RDR2 (Rockstar Social Club), and the same logic covers Ubisoft Connect and EA App titles. Also excluded: **all free-to-play games and their DLC** — so the DMZ provides nothing for your F2P launch track. Cyberpunk 2077 and Black Myth: Wukong look fine. Your AAA list is roughly half-eligible.

**Household intent and monitoring.** Valve states Steam Families is "intended for a household of up to 6 close family members" and that they "expect the requirements for participating in a Steam Family to change over time as we monitor its usage." A platform-wide pattern of two-account families whose junior member logs in from rotating IPs across a city is exactly the signal that triggers a rule change. This is a policy dependency you do not control, and the whole architecture rests on it.

**Slot cooldowns make recovery expensive.** Adults must wait one year from joining a family before joining another, and each vacated slot has a one-year cooldown. If a user's setup goes wrong, they are locked out of restructuring for twelve months.

### Better mechanism: Steam's native QR / device-code login

Steam's mobile app supports QR sign-in. The user scans a code with their phone; **the password and the Guard code never enter the node at all.** This kills the strongest attack in the threat model — keylogging credentials at the login prompt — using a first-party feature, with no fake family, no VAC propagation channel, and no dependency on Valve tolerating anything.

Residual risk is honest and smaller: the session token still lands in memory on the node and can be stolen. But a stolen token is bounded — Steam requires mobile confirmation for trades and market listings, so inventory is not trivially drainable, and there is no propagation path to a ban on a separate account.

Combine with: session-scoped lifetime, forced logout and token revocation at session end, operator KYC plus a slashable bond, and a plainly-worded disclosure of the residual risk. That stack is defensible. The DMZ is not.

---

## 3. Anti-cheat segregation — directionally right, one factual error

**Keep:** strict segregation of the competitive-F2P path from the VM-based AAA path, and never mixing them on the same host image. That is correct and it is the right instinct about which risks compose badly.

**The factual error:**

> "Narrative AAA (Cyberpunk, Witcher, Hogwarts Legacy): These use Denuvo or standard Steam DRM. They do not care about virtual machines."

The category heuristic is unreliable. **Elden Ring — on your own earlier AAA list — ships EasyAntiCheat and runs it in single-player by default.** You have to explicitly launch the offline executable to avoid it. Several other single-player and co-op titles ship EAC or BattlEye similarly.

"Narrative AAA is anti-cheat free" is not a safe assumption to route traffic on. You need a **per-title verified allowlist**, populated by actually testing each title, with an explicit field in the catalogue. Not a genre inference.

That is also a schema change worth making early: a title record needs `antiCheat: none | vac | eac | battleye | vanguard` and `drm: none | steam | denuvo | thirdPartyLauncher`, because both fields become hard filters in matching.

**On the bare-metal suggestion:** reimaging hosts between sessions to escape VM detection is technically real but operationally brutal on consumer hardware — PXE infrastructure, ten-plus minute reimage cycles, and it wipes the provider's own OS. That is a datacenter play, not a home-provider play. It does not fit your supply model.

**On Denuvo and VMs:** Denuvo does perform virtualisation checks, so the claim that these titles "do not care about virtual machines" is also questionable independent of anti-cheat. This is unverified and worth testing rather than assuming — see the test plan below.

---

## 4. Hardware spoofing + ssfn injection — do not build this

This is the part I want to be unambiguous about, because everything up to here has been a business-risk conversation and this is not.

### 4a. Injecting the ssfn file is the credential honeypot, rebuilt

The `ssfn` file **is** the Steam Guard machine authorisation token. "Inject the Steam Sentry file into the VM at boot" means:

- Your orchestrator **stores** Steam Guard authentication material for every user, permanently. That is the centralised credential honeypot we explicitly rejected.
- You **push** it onto untrusted hardware before each session, so every provider receives a copy.
- A stolen `ssfn` plus a password yields account access **with 2FA already satisfied**. You have not just stored credentials, you have disabled the second factor.

This is strictly worse than the problem it solves. It defeats the exact control that currently protects your users.

### 4b. Spoofing hardware IDs to defeat DRM is a different legal category

Every problem discussed so far has been **civil**: breach of contract with Valve. Worst realistic outcome is account bans and a contract claim from one counterparty.

Anti-circumvention law is **criminal**, and the claim belongs to **every publisher whose DRM you defeat**, not just Valve.

Denuvo is a technological protection measure protecting a copyrighted work. A system whose stated design purpose is to make Denuvo believe the hardware is unchanged, so that its activation controls do not engage, is circumvention of a technological protection measure. That is the textbook definition, and the intent is documented in your own architecture.

Under India's Copyright Act 1957, **Section 65A** (inserted by the 2012 Amendment) criminalises circumvention of an effective technological measure applied to protect a copyright, with imprisonment and fine. The US DMCA §1201 is broader still: §1201(a)(2) prohibits **trafficking** in circumvention technology — and a marketplace distributing a QEMU spoofing configuration to its provider fleet is trafficking, not merely circumventing. The EU InfoSoc Directive Article 6 has an equivalent trafficking prohibition.

Three consequences that matter more than the abstract exposure:

1. **It is documented and deliberate.** "Spoof SMBIOS so Denuvo never locks the game" in a design document is evidence of intent. Intent is what separates a takedown notice from a prosecution.
2. **It reaches you personally.** Corporate structure protects far less against criminal provisions and personal-liability doctrines than it does against contract claims.
3. **It is indistinguishable from the HWID-spoofer market.** Spoofing SMBIOS UUID, CPUID, and MAC to defeat hardware fingerprinting is precisely what commercial HWID spoofers sell to banned cheaters. If your platform ships that capability, you are in that business as far as any publisher's legal team is concerned.

Also note the SSA clause I pulled directly:

> "You agree that you will not directly or indirectly disable, circumvent, or otherwise interfere with the operation of software designed to prevent or report the use of Cheats. You agree that you will not tamper with the execution of Steam."

Hardware-ID spoofing to make anti-cheat and Steam Guard misidentify the machine sits squarely inside that sentence, twice.

### 4c. It also loses on the engineering merits

Even setting law aside: spoofing SMBIOS does not hide a hypervisor. Detection vectors include the CPUID hypervisor present bit, RDTSC timing analysis, ACPI table signatures, PCI device IDs, MSR behaviour, and TSC frequency artefacts. You would be in an arms race against Denuvo and Riot — organisations with more full-time engineers on VM detection than your company will have employees — and **a single Denuvo update can break your entire fleet simultaneously.** Your uptime becomes a function of an adversary's release schedule.

### The Denuvo activation-limit claim itself needs verification

The "5 activations per 24 hours" figure is widely repeated but originates from 2017–2018 reporting, and Denuvo's activation policy is understood to be **configurable per title by the publisher** rather than a fixed global constant. Some titles are reported to allow more, some fewer. What happens at the limit — a rolling cooldown versus a hard lock — also matters enormously for your design and is not well documented publicly.

I have research running on this. **Do not architect around the specific number until it is confirmed**, because if the real behaviour is a 24-hour rolling window that simply expires, the problem may be a UX annoyance affecting heavy users rather than a structural blocker at all — and the entire spoofing proposal would be solving a problem that mostly does not exist.

That said: **even if the limit is exactly as described, the answer is not to spoof it.** The answer is a scheduling constraint — cap how many distinct physical hosts a given user's Denuvo-protected title can touch per rolling 24 hours, and prefer re-matching that user to hosts they have already activated on. That is host affinity, it is a matching-layer change, and it is completely legal. It costs you some placement flexibility and nothing else.

---

## 5. The meta-pattern worth naming

Three of these four proposals share a shape: **make an untrusted machine look trusted to a DRM system.**

That framing loses structurally, for three reasons. It is an arms race against better-resourced adversaries. It converts civil exposure into criminal exposure. And it makes your platform's reliability dependent on your adversary's patch cadence.

The inverse framing wins: **make the machine actually trustworthy, and prove it.** Operator KYC, financial bonds that get slashed, hardware attestation, reputation built from session history, credentials that never enter the node in the first place. That path is slower and less clever. It is also the only one that survives contact with a publisher's legal team, and it compounds — every trusted operator you accumulate is permanent inventory, whereas every spoofing trick is a depreciating asset.

---

## 6. What to actually do next

**Build now:**

1. Title Sharding for F2P, indie, and compute images — orchestrator-dictated storage, demand-driven provisioning, shard-aware matching as a hard filter.
2. Extend the catalogue schema with `antiCheat` and `drm` fields; make both hard filters in `matching.ts`.
3. Host affinity in the matcher: prefer previously-used hosts per user per title. Legal, and it independently mitigates the Denuvo issue whatever its real parameters turn out to be.

**Adopt instead of the DMZ:**

4. QR / device-code login so credentials never touch the node. Session-scoped tokens, forced revocation at session end.
5. Operator KYC plus slashable bond. Honest written disclosure of residual risk.

**Test before assuming:**

6. Anti-cheat behaviour per title, on a throwaway account, on hardware you do not care about. Elden Ring specifically, since it disproves the category heuristic.
7. Denuvo activation behaviour — how many hosts before it complains, and whether it recovers.
8. Steam Guard behaviour across rotating machines with QR login, over several days.

**Do not build:** ssfn injection, SMBIOS/CPUID/MAC spoofing, peer-to-peer game file distribution, shared marketplace game accounts.

**Ask Valve:** whether café-style floating licences can extend to remote streaming, and whether third-party depot caching is acceptable. Both are free to ask and both unlock real capability if answered favourably.
