# Game Licensing — The Hard Problem and the Ways Around It

**For:** Decentralised P2P Cloud Gaming Marketplace
**Question:** A user must legally own a game to play it. So how does a rented stranger's PC run it — and how do we avoid making the player wait for a 100GB download?
**Verified:** 2026-08-06, quotes taken from live licence pages.

---

## 1. What the law/licence actually says

### Steam Subscriber Agreement
Source: https://store.steampowered.com/subscriber_agreement/

> "Valve hereby grants, and you accept, a non-exclusive license and right, to use the Content and Services **for your personal, non-commercial use**"

> "You are entitled to use the Content and Services for your own personal use, but you are **not** entitled to: (i) sell, grant a security interest in or transfer reproductions of the Content and Services to other parties in any way, nor to **rent, lease or license the Content and Services to others without the prior written consent of Valve**"

> "You may **not reveal, share or otherwise allow others to use your password or Account**"

> "you must not use your Account to **enable a violation of this Agreement by others**, such as through their commercial use of Steam Content and Services"

**Three separate prohibitions, and our naive design violates all three:**

| Naive design | Clause it breaks |
|---|---|
| Node operator installs the game, player rents access | "not entitled to rent, lease or license the Content to others" |
| Player logs into their Steam account on the operator's PC | "may not reveal, share or otherwise allow others to use your password or Account" |
| Operator earns money from it | "personal, non-commercial use" |

**So: the node operator can never supply the licence. Full stop.** Any design where the operator's copy of a game is what the player plays is illegal, and no amount of clever architecture fixes it.

---

## 2. How GeForce NOW legally solves it — BYOL

Source: https://www.nvidia.com/en-us/geforce-now/faq/

> "**Do I need to own games? Yes**, you need to own or purchase a game from one of the supported game stores before playing it on GeForce NOW."

> "Connect to your favorite game store accounts and **stream games you own**"

> "Games must be accessed from the digital stores. You will be prompted to **log in to verify that you own the game** before you can play it"

**The model is Bring Your Own Licence (BYOL).** NVIDIA never owns or supplies the game. The player authenticates to *their own* Steam/Epic account inside the streaming session; the node is just rented hardware executing the player's own licence.

This is the only model that works, and it's the one we must copy.

### But there's a second gate — publisher opt-in

> "premium members have access to Install-to-Play games, which they can install, download and play thousands of additional Steam games **that have opted-in to Steam Cloud Gaming by the game publisher**"

> "Install-to-Play games are titles you can install and play from your own Steam library, **as long as the publisher has opted in to support Steam Cloud Gaming**"

So even with BYOL, publishers must individually opt in. NVIDIA — a company worth trillions with a formal Valve partnership — still cannot stream a title whose publisher hasn't consented.

**We will not get blanket publisher opt-in as a student startup.** Plan accordingly.

---

## 3. The download problem

Even once licensing is solved, the player can't wait 45 minutes for a 100GB install. How GFN handles it:

- **Ready-to-Play:** ~4,500 titles pre-installed and maintained on NVIDIA's own infrastructure, "always kept up to date"
- **Install-to-Play:** player installs it themselves, and can "optionally **purchase a storage plan** to keep your installed games and saved data in the cloud"

NVIDIA either pre-caches at datacenter scale, or charges the user to keep persistent storage. Both need infrastructure control we don't have over strangers' PCs.

### Our version: content-addressed cache + cache-aware matching

*(This section is engineering design, not quoted from a source.)*

The download problem is actually where a P2P network has a **structural advantage** over GFN, and it should become a core feature:

1. **Nodes advertise their cache.** Each node reports which title IDs and versions it already has on disk. This becomes a matching dimension alongside GPU class and latency.

2. **Matcher prefers warm nodes.** Route the player to a node that already has the title. `has_title AND region_ok AND latency<120ms` beats raw GPU specs every time — a cold node is useless regardless of how fast it is.

3. **P2P chunk distribution between nodes.** When a node lacks a title, it pulls content-addressed chunks from *peer nodes* rather than re-downloading from origin. Nodes in the same city move data at LAN speed. This is what a P2P network is genuinely good at, and GFN structurally cannot do it.

4. **Read-only base + copy-on-write overlay.** Game files sit in an immutable base layer; each session gets a disposable overlay for saves/config, destroyed at session end. One install serves many sessions with no cross-contamination.

5. **Operator incentives for cache warmth.** Pay operators a small retainer to keep popular titles cached and updated. Cache warmth is inventory — treat it like stock.

**Important caveat:** steps 1–3 apply cleanly to *licence-free* content (F2P clients, our own builds, open-source games). For paid titles under BYOL, redistributing game binaries between nodes is itself a "transfer of reproductions" and is **not** legal without publisher consent. So cache-sharing is only safe for the content classes in section 4.

---

## 4. The three viable go-to-market paths

### PATH A — Free-to-play first ⭐ STRONGEST FOR INDIA

**F2P games have no purchase requirement, so the entire rental problem evaporates.** There is no licence to rent, transfer, or share. The player logs into their own game account — which is the normal, expected flow for F2P — and the client is freely redistributable.

India's actual gaming market is overwhelmingly F2P: BGMI, Free Fire, Valorant, Genshin Impact, Call of Duty Mobile, Apex, Fortnite.

This aligns exactly with the existing strategy of targeting India + latency-sensitive gaming:
- No publisher opt-in negotiation needed to *start*
- Clients are freely downloadable → cache-sharing between nodes is legal
- Enormous Indian user base on low-end hardware (the precise demographic that wants borrowed GPU power)
- Competitive shooters are the most latency-sensitive genre → our sub-120ms moat matters most exactly here

Still verify each title's own EULA and anti-cheat stance before launch (see risks below). But this is the wedge with no licensing wall in front of it.

### PATH B — Indie / own-IP partnerships

Get **written** permission from indie studios — Valve's own wording is "without the prior written consent of Valve," so written consent is the mechanism the licence itself anticipates.

Indie studios are reachable as a student founder, benefit from a distribution channel in India, and can sign a simple streaming addendum. Matches the existing "target India/indie studios" strategy. Slower, but it's the path to a defensible catalogue.

### PATH C — Non-gaming GPU workloads

Blender/Unreal rendering, 3D generation, ML inference, video encoding. No game licences involved at all. This is the batch-compute track and it has zero licensing risk — which is precisely why it's the right *backup* track.

---

## 5. What NOT to build

| Design | Why it's fatal |
|---|---|
| Node operator installs game, rents access | Direct breach: "not entitled to rent, lease or license the Content to others" |
| Player hands over Steam credentials to run on operator's PC | Breach of "may not reveal, share or otherwise allow others to use your password"; also hands a stranger the player's account |
| Shared "marketplace Steam account" with a game library | Breach of account-sharing + commercial-use clauses. Instant ban and likely legal action |
| Redistributing paid game binaries between nodes | "transfer reproductions of the Content and Services to other parties in any way" |

**The credential problem deserves emphasis.** Under BYOL the player types their Steam password into a session running on an untrusted stranger's machine. That operator could keylog, screen-scrape, or dump memory. GFN avoids this because NVIDIA is a single trusted operator running attested infrastructure.

For an untrusted P2P supply side, mitigations are: OAuth/QR-based login where credentials never touch the node; ephemeral hardware-isolated VMs; TEE/attestation; KYC'd and bonded operators; slashing reputation stakes. **None of these fully solve it.** This is the single hardest trust problem in the whole product and it deserves its own design doc.

---

## 5b. The "pre-installed game, player logs into their own account" design

**The proposal:** node operator pre-installs AAA titles. Steam client sits logged OUT. Player connects, logs into their *own* Steam account, Steam validates that *they* own the title, game launches instantly from the already-present files. Session ends, account logged out and wiped.

### Why this is the right architecture

This is not a workaround — it is precisely how GeForce NOW **Install-to-Play** works, and it fixes both problems at once:

| Problem | How this design solves it |
|---|---|
| Operator can't supply the licence | They don't. Player brings their own. Operator supplies *hardware only* |
| 100GB download wait | Files already on disk. Player's login just validates entitlement |
| Who enforces ownership? | **Steam itself.** If the player doesn't own it, Steam refuses to launch |

That third row is the strongest part of the idea. **Licence enforcement is delegated to Valve's own client** — we never have to police ownership, and we can never accidentally serve a game to someone who hasn't bought it. Architecturally this is clean.

Valve's own partner docs confirm the ephemeral-session model is expected:

> "Each time a user plays a game via Cloud Play they **may be playing from a new virtual PC**. For this reason it is very important that your game has Steam Cloud enabled or has a separate online save system."
> — https://partner.steamgames.com/doc/features/cloudgaming

So per-session wipe + cloud saves is the sanctioned pattern, not a hack.

### The gate that blocks it: a provider whitelist, not just a game whitelist

Source: https://partner.steamgames.com/doc/features/cloudgaming

> "Developers must **manually opt-in** the games they wish to make available on GeForce NOW... **We are using a whitelist of games** that have signed up in Steamworks."

And the developer-side opt-in is a checkbox naming **specific, individually approved providers**:

> "Find the "Cloud Play" section and select two boxes 'Enable your game to run streamed from the Cloud, **hosted by Valve, and the following service providers:**' and '**NVIDIA GeForce NOW**.'"

Plus a signed contract with Valve:

> "The Actual Authority user of your Steamworks account must sign the new **Steam Cloud Gaming Addendum**"

And new providers are added at **Valve's** initiative, not by application:

> "Will there be other cloud gaming services added to Steam Cloud Play? **We may add additional Steam Cloud Play services in the future. At that time we would reach out to you** to opt your games into the new service."

**This is a two-layer permission system:**
1. Valve approves the *streaming provider* (currently: Valve + NVIDIA GFN only)
2. Each developer then opts in *their game* to that named provider

We fail at layer 1. There is no public application process — Valve reaches out. Until a provider is on that list, no developer *can* tick a box for us even if they wanted to. The programme is also still labelled **Beta**, "accepting a limited amount of games."

### The remaining hard problems

*(Engineering/legal judgment, not quoted from a source — flagged as such.)*

1. **Credentials on untrusted hardware — still unsolved, and worse here.** The player types their Steam password + Steam Guard code into a session on a stranger's PC. A malicious operator can keylog, screen-scrape, dump memory, or steal the session token. Stealing a *Steam session token* is worse than a game licence — it's the player's entire library, payment methods, and inventory. GFN escapes this because NVIDIA is one trusted, attested operator. We would have thousands of anonymous ones.

2. **Steam Guard will fight this by design.** Every login from a new machine triggers device verification. Constantly logging one account into rotating unknown machines is exactly the fingerprint of account-selling/boosting, and is a plausible trigger for lockouts or bans. We'd be asking players to make their account look compromised.

3. **Whose copy is on disk?** The pre-installed files were downloaded under the *operator's* account. Having the operator's reproduction on disk, activated by a third party's licence, is at minimum arguable against the SSA's ban on transferring "reproductions of the Content and Services to other parties in any way." Untested, and not a fight to pick.

4. **Anti-cheat.** Unchanged from section 7 — VM/remote-execution hostility applies regardless of who owns the licence.

### Verdict

**Right architecture, no permission to run it — for Steam AAA titles specifically.**

Keep this design. It is the correct end-state and the thing we build toward. But it cannot legally launch on paid Steam titles without being a whitelisted Steam Cloud Play provider, and that door is currently opened only by Valve.

**What it changes today:** the "pre-installed + player brings licence" pattern is legally fine wherever *no whitelist governs it*:
- **F2P titles** (Path A) — no purchase, no licence to transfer, and pre-installing the client kills the download wait. Combine this design with Path A immediately.
- **Indie titles** (Path B) — a studio can grant written consent directly, since they own the IP. Pre-installing their game on nodes is exactly what our addendum should authorise.
- **Own/open-source builds and batch render workloads** — no gate at all.

So: build the pre-install + BYOL + ephemeral-session machinery now, aim it at F2P and indie, and it's already the same machinery that would serve AAA the day a Cloud Play addendum ever becomes reachable.

---

## 5c. DECISION RECORD — "Provider owns the game, renter plays it without logging in"

**Asked repeatedly. Answering once, definitively.**

**Question:** The provider owns GTA 5. The renter connects, never logs into any account, and plays the provider's copy. Legal?

**Answer: No.** This is not a grey area, an edge case, or an enforcement gamble. It is the exact conduct the Steam Subscriber Agreement's rental clause exists to prohibit, and it breaks four clauses at once:

| Clause | Text | How this breaks it |
|---|---|---|
| Rental | "you are **not** entitled to... rent, lease or license the Content and Services to others without the prior written consent of Valve" | Renting the provider's copy to a stranger, for money |
| Account sharing | "You may **not** reveal, share or otherwise allow others to use your password or **Account**" | The renter is using the provider's logged-in account |
| Non-commercial | "use the Content and Services for your **personal, non-commercial use**" | It is a paid commercial transaction |
| Enabling others | "you must not use your Account to **enable a violation of this Agreement by others**, such as through their commercial use" | The marketplace induces this at scale |

### The reasoning trap to avoid

"I bought the game, it's mine, I can do what I want with it."

**You did not buy the game. You bought a licence to use it.** The SSA says so directly — Steam sells "the right to use" Content, not ownership of it. A licence is defined *entirely* by the permissions written into it. "Personal, non-commercial" and "no rental" are two of those permissions. Renting out access is not an exercise of ownership; it is use outside the licence grant.

The physical-goods intuition (I own this disc, I can lend it) does not transfer. And even then — lending a disc means *you* stop playing. Here the provider retains their copy and monetises simultaneous access by others.

### Related mechanisms that do NOT rescue this

- **Steam Family Sharing** — restricted to family/household members, blocks simultaneous play of the same library, and is explicitly non-commercial. Does not cover paying strangers.
- **Offline mode** — launching the provider's copy offline to skip the ownership check is licence circumvention, not a UX optimisation. See §5b.
- **A shared marketplace-owned account** — same violation, centralised, and *more* incriminating because it is deliberate and documented.

### Enforcement is not theoretical

Concurrent-session detection, hardware-fingerprint churn on one account, IP geography churn, and VAC telemetry all surface this pattern. Consequence ladder: account lock → library forfeiture → marketplace-wide bans → publisher legal action against the *operator*, not the users. A marketplace that systematises the breach is the defendant.

### The one mechanism that makes it legal

**Steam PC Café floating licences.** This is precisely the model above, productised and permitted — see `LICENSING-SOLUTION.md`. Valve's own words:

> "Use a **single Steam account** to purchase additional game licenses and **share them with visitors — customers or guests alike** — via your local network."

That is provider-supplies-the-licence, legally. It works because the operator buys **commercial** licences, not consumer ones, under a separate agreement with Valve.

**The unresolved constraint:** the café programme is written around *local network* venues. Whether it can cover remotely-streamed machines is the open question — and is exactly why "ask Valve directly" is Stage 2 of the strategy. Until answered, assume it does not.

### Standing rule

> Under a **consumer** licence: the renter's own account launches the game. Always. No exceptions.
> Provider-supplied licences require a **commercial** licence agreement, obtained in writing, first.

---

## 6. Recommendation

1. **Launch on F2P titles only.** No licensing wall, huge Indian market, maximum latency sensitivity. Prove sub-120ms matching works with real players.
2. **Run batch/render compute in parallel** as the zero-licensing-risk revenue track.
3. **Sign indie studios one at a time** with written streaming consent to build a paid catalogue.
4. **Never touch AAA paid titles** until there is a real publisher opt-in programme — that requires a company, lawyers, and leverage we don't have yet.
5. **Treat cache warmth as inventory** and cache-aware matching as a core feature, not an optimisation.
6. **Write a separate threat model** for credential handling on untrusted nodes before any paid-title work.

---

## 7. Open questions to resolve

- Individual F2P EULAs: do BGMI/Valorant/Genshin permit play on rented remote hardware? Each must be checked separately.
- **Anti-cheat is a serious unknown.** Vanguard, BattlEye, and EAC are hostile to VMs and to unrecognised remote-execution environments. A competitive-shooter strategy could be blocked at the anti-cheat layer even where the EULA permits it. This needs testing early — it could invalidate Path A for the most valuable titles.
- Indian IT Act / DMCA-equivalent exposure for a marketplace intermediary in India.
- Whether Valve would ever grant written consent to a small operator, and what that process looks like.
