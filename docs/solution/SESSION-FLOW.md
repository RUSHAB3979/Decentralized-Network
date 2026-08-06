# Session Flow — Killing the Download Wait Without Breaking the Licence

**For:** Decentralised P2P Cloud Gaming Marketplace
**Problem:** "User books session → game not installed → 2 hours downloading" is an unusable product.
**Answer:** Pre-caching is correct. But cache the *files*, never the *licence*.

---

## The one distinction that decides everything

> **Pre-caching FILES ≠ pre-supplying LICENCES.**

The 100GB download is the real pain. The 30-second login is not.

So: keep the pre-install (kills the download), keep Bring-Your-Own-Licence (keeps it legal). You lose ~30 seconds of UX and you stay out of court.

| | Files on provider's disk | Licence executed |
|---|---|---|
| **LEGAL (BYOL)** | Provider pre-caches game files | **Renter's own account** validates entitlement |
| **ILLEGAL** | Provider pre-caches game files | **Provider's account** supplies the game |

Identical from an engineering standpoint. Opposite from a legal standpoint. The difference is one field: *whose credential launches the binary.*

---

## What "READY" means on a provider listing

**"READY" = 0 minute download. It does NOT mean "game included."**

```
Arjun's Gaming Rig — Mumbai
RTX 4080 | 16GB VRAM | 500 Mbps up | 12ms
₹50/hour | 4.9★ (234 sessions)

CACHED — no download wait:
  Valorant          READY  (F2P — just log in)
  Genshin Impact    READY  (F2P — just log in)
  BGMI              READY  (F2P — just log in)
  Hades II          READY  (bring your own licence)

NOT CACHED:
  Baldur's Gate 3   ~45 min first-time download
```

The marketplace filter still works exactly as intended — user searches a title, sees who has it warm, books, connects, plays. **The search-by-game filter is a genuinely great feature and it survives intact.** That is the killer UX, not the login skip.

---

## The realistic 90-second flow (legal version)

```
00:00  User searches "Valorant", filters: <20ms, cached
00:10  Picks Arjun's rig — READY, 12ms, ₹50/hr
00:15  Books. Session container spins up on Arjun's node
00:25  WebRTC stream connects. Windows session, game pre-launched
00:35  User logs into THEIR OWN Riot account
00:60  In game

Total: ~60-90 seconds. Zero download.
```

For a paid title under BYOL, add one step: the user logs into their own Steam first, Steam validates *their* entitlement, game launches from the pre-cached files. ~90-120 seconds.

**Still faster than cold-booting a local PC.** The download was the killer; it's gone.

---

## The genuinely great idea: scheduled cache warming

This is the strongest part of the proposal and it should be built.

```
User books a session for tomorrow 8pm
  → Provider daemon queues the download tonight
  → Small non-refundable reservation fee (covers provider bandwidth)
  → By 8pm the title is warm
  → User connects to zero wait
```

This turns the cold-cache problem into a **scheduling** problem, and scheduling problems are solvable. Cafés, restaurants and cloud providers all work this way.

It also creates a real economic flywheel:

```
Provider with nothing cached     → generic compute       → ₹25-30/hr
Provider with 5 popular titles   → targeted bookings     → ₹50-60/hr
                                 → higher utilisation
                                 → better reviews (no waits)
```

Nobody has to be forced to maintain a library. The market does it. **Cache warmth is inventory** — and inventory that self-organises is a real moat.

---

## Cold-start honesty

Show the truth in the UI, always:

```
Baldur's Gate 3 on this provider:
  ~45 min first-time download
  [Book anyway]  [Find a cached provider]  [Schedule for later]
```

Never hide a wait. A user who chooses a 45-minute wait knowingly is fine. A user ambushed by one never comes back.

---

## FOUR THINGS THAT MUST NEVER BE BUILT

These were proposed in good faith as UX fixes. Each one is fatal.

### 1. Provider's own copy played by the renter
Provider installs GTA 5 under their account, renter plays it. This is the single clause the Steam Subscriber Agreement exists to forbid:

> "you are **not** entitled to... **rent, lease or license the Content and Services to others** without the prior written consent of Valve"

Not a grey area. This is the definition of the prohibited act.

### 2. A shared "Nexus session" Steam account
A marketplace-owned account holding a game library that renters play from. This breaks three clauses simultaneously:

> "You may **not reveal, share or otherwise allow others to use your password or Account**"

> "use the Content and Services for your **personal, non-commercial use**"

> "you must not use your Account to **enable a violation of this Agreement by others**, such as through their commercial use"

Outcome: mass account bans, and a documented, deliberate, commercial breach — which is what turns a ban into a lawsuit. **This is the most dangerous idea in the entire proposal.**

### 3. The "Steam Offline Mode trick" to skip user login
Launching a paid game in offline mode under the provider's licence so the renter doesn't have to log in is not a UX optimisation — it is licence circumvention with extra steps. The word "trick" is the tell. If a mechanism exists *specifically* to avoid the ownership check, that mechanism is the offence.

### 4. Storing user credentials for background auto-login
Encrypting users' Steam/Rockstar passwords in our DB and injecting them into strangers' machines is worse than the problem it solves:

- It builds a centralised honeypot of gaming credentials — a top-tier breach target
- It still exposes plaintext credentials to a malicious node at injection time
- Steam Guard triggers on every new machine anyway, so it does not even work reliably
- The traffic pattern is indistinguishable from credential stuffing, and will be treated as such

"0 seconds extra" is not achievable legally or securely. **Accept 30-60 seconds of login. It is the cost of not being a criminal enterprise, and it is cheap.**

---

## The Shadow comparison, corrected

The claim "we're better than Shadow because Shadow gives you a blank PC" is true on UX and dangerous on law.

**Shadow's blankness IS its legal shield.** They never touch the licence chain, which is exactly why they run AAA titles without being on Steam's Cloud Play whitelist. "Better than Shadow" in the proposed sense means "we removed the thing that made it legal."

The honest version of the advantage:

> Shadow: blank PC, you install everything, hours of setup
> Us: **your** licence, **our** pre-cached files, 90 seconds to play

That is still a real and defensible advantage. We eliminate the *download*, not the *ownership check*.

---

## Catalogue reality check

Every title named in the original proposal — GTA 5, Cyberpunk 2077, RDR2, Elden Ring, Witcher 3, Baldur's Gate 3 — is a paid AAA title, i.e. the exact category gated behind the Steam Cloud Play provider whitelist (see `GAME-LICENSING-PROBLEM.md` §5b). Rockstar Social Club in particular has a notably restrictive EULA.

**Launch catalogue is F2P + indie** (`LICENSING-SOLUTION.md`). The pre-cache architecture works identically for those titles — and for F2P there is no ownership check at all, so the flow is genuinely ~60 seconds.

---

## Build order

This is **not** a Phase 2 bolt-on. The "whose credential launches the binary" decision determines session isolation, wipe policy, and credential handling — it is a Phase 1 architectural choice.

1. **Phase 1** — session container with clean wipe; BYOL login; cache manifest per node (title ID + version + bytes)
2. **Phase 1** — matcher scores on `has_title AND region AND latency`, not raw GPU specs. A cold fast node loses to a warm adequate one
3. **Phase 2** — scheduled cache warming + reservation fees
4. **Phase 2** — peer-to-peer chunk distribution between nodes (**licence-free content only** — redistributing paid binaries is "transfer of reproductions")
5. **Phase 3** — cache-warmth retainers for providers

---

## Summary

The diagnosis was right: pre-installation is the fix, and every major cloud gaming platform does it.

The product instincts were right: game-library filtering, scheduled warming, and provider economics are all genuinely good, and the scheduled-warming idea is a real contribution.

The licensing shortcuts were wrong, and four of them are company-ending.

Keep all the UX. Change one field: **the renter's credential launches the game, always.**
