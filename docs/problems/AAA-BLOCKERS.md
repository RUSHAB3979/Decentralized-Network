# What Actually Blocks AAA Titles Right Now

**For:** Decentralised P2P Cloud Gaming Marketplace
**Question:** Under BYOL the licence problem is solved. So what is *actually* stopping AAA hosting today?

---

## Correction to earlier analysis

Previous docs treated **law** as the primary AAA blocker. That over-weighted it.

Under Bring-Your-Own-Licence, the legal position is much stronger than implied:

- The player uses **their own** licence, for **their own** personal play — inside the "personal, non-commercial use" grant
- The player rents **hardware**, not content. They are not renting content *to* anyone, so the rental clause does not bind them
- The operator never touches the licence chain, so the operator has nothing to be licensed *for*

**The Shadow precedent proves this.** Shadow runs AAA titles today, is not on the Steam Cloud Play provider whitelist, and never negotiated with Valve — because renting a computer is not licensing a game.

**The Steam Cloud Play whitelist only binds a *catalogue* provider** — someone who provisions a game library and streams it. It does not bind a hardware-rental model. Earlier docs applied it too broadly.

So the real blockers are not legal. They are **trust, anti-cheat, and unit economics** — and each is independently sufficient to stop AAA today.

---

## BLOCKER 1 — Credential exposure on untrusted hardware (the real one)

Under BYOL the player must type their **Steam password + Steam Guard code** into a Windows session running on **a stranger's PC that the stranger fully controls**.

The operator has kernel-level access to their own machine. They can:

- Keylog the login
- Dump session tokens from process memory
- Screen-record the Steam Guard prompt
- Persist a stealer that survives session wipe

A stolen Steam session token is not one game — it is the **entire library, payment methods, and CS2/TF2 inventory**. Inventories alone can be worth more than the hardware.

**Why competitors don't have this problem:**

| | Who runs the machine | Credential risk |
|---|---|---|
| GeForce NOW | NVIDIA datacenter | Single trusted operator |
| Shadow | Shadow datacenter | Single trusted operator |
| **P2P network** | **Anonymous strangers' home PCs** | **Every session is a new trust decision** |

Mitigations exist and none fully solve it: QR/OAuth login where credentials never enter the node, hardware-attested boot, operator KYC + slashable bonds, session-scoped tokens. **This needs its own threat model before AAA is viable.**

This is the hardest unsolved problem in the product. Not the law.

---

## BLOCKER 2 — Anti-cheat (the one that can hurt *users*, not us)

Kernel anti-cheat (Riot Vanguard, EasyAntiCheat, BattlEye) is hostile to virtualised and remote-execution environments and fingerprints hardware.

Why this is worse than a normal blocker: **bans land on the player's account, not ours.** A player HWID-banned from Valorant because they used our service is a catastrophic outcome we cannot reverse, and it destroys word-of-mouth in exactly the market we are targeting.

Note this also constrains parts of the **F2P wedge** — Valorant and BGMI are F2P but heavily anti-cheat protected. It is not purely an AAA issue.

**Status: UNVERIFIED in this session.** No source consulted. Must be tested empirically before either track launches — see "What to test" below.

---

## BLOCKER 3 — Disk economics at the edge

AAA titles run roughly 60–150GB each (approximate, varies by title and install options).

A typical home operator with a 1TB SSD, after Windows and their own games, might keep **6–10 AAA titles** warm. Across a catalogue of thousands, edge cache coverage is structurally thin.

| | Storage model | Catalogue breadth |
|---|---|---|
| GeForce NOW | Datacenter, petabyte-scale | ~4,500 titles pre-installed |
| **P2P network** | **Consumer SSDs at the edge** | **~6–10 titles per node** |

This is why **cache-warmth matching is not an optimisation, it is the core scheduling problem.** A cold node is useless regardless of GPU class.

It also caps AAA breadth in a way it does not cap F2P: the top Indian F2P titles number in the *dozens*, and are far smaller. A handful of cached titles covers most of that demand. The same handful covers almost none of AAA demand.

---

## BLOCKER 4 — Login friction stacks badly

Even with a perfect cache, AAA login is not one step:

```
Steam login  →  Steam Guard device approval (new machine EVERY session)
             →  publisher launcher (Rockstar Social Club / EA App / Ubisoft Connect)
             →  that launcher's own login + device check
             →  game
```

Two independent problems:

1. **Steam Guard fires on every new machine.** In a P2P network the machine changes every session, so this is permanent friction, not a one-time setup cost. Worse, one account logging into rotating unknown machines is the exact behavioural fingerprint of account-selling — it makes a legitimate user look compromised.
2. **Each publisher launcher has its own EULA and device checks**, stacked on top of Steam's. Rockstar Social Club is notably restrictive.

F2P titles mostly collapse this to a single in-game account login.

---

## Ranked summary

| # | Blocker | Severity | Solvable? |
|---|---|---|---|
| 1 | Credential exposure on untrusted nodes | **Fatal** | Hard — needs threat model, KYC, bonds, tokenised login |
| 2 | Anti-cheat bans on player accounts | **Fatal if triggered** | Unknown — **must test** |
| 3 | Disk economics at the edge | Structural | Manageable via cache-warmth matching + retainers |
| 4 | Login friction / Steam Guard churn | Severe UX | Partially — QR/OAuth login helps |
| 5 | Cloud Play whitelist | **Only if we present as a catalogue provider** | Avoidable by using the hardware-rental framing |

**None of the top four are legal problems.** The licence question — which consumed the most analysis — turns out to be the *least* binding constraint under BYOL.

---

## Why F2P-first is still right, for different reasons than stated

Earlier docs justified F2P-first on **licensing**. That justification was weaker than claimed. The stronger justification is operational:

- **Blocker 1 shrinks** — a throwaway Genshin/BGMI account is a far smaller loss than a full Steam library with payment methods attached
- **Blocker 3 disappears** — F2P titles are smaller and the demand catalogue is dozens of titles, not thousands
- **Blocker 4 mostly disappears** — one in-game login, no Steam Guard churn, no publisher launcher chain
- **Blocker 2 remains** — and is the reason to test anti-cheat *before* committing to the wedge

F2P-first is correct. But it is correct because it de-risks trust and economics, not because AAA is legally impossible.

---

## What to test this week (cheap, decisive)

1. **Anti-cheat on remote/virtualised hardware.** Install Valorant (Vanguard, the strictest) on a spare or friend's machine, access it over Parsec/Moonlight, and see whether it launches, warns, or bans. Repeat for BGMI (F2P) and one EAC title. **This is the single highest-information test available and it costs nothing.**
2. **Steam Guard behaviour on rotating machines.** Log one test account into 3–4 different machines over a few days. Measure the friction and watch for lockouts.
3. **Real cache-warm inventory.** Survey what titles friends with gaming rigs actually have installed. That is your real day-one supply catalogue.

Test 1 can invalidate part of the F2P wedge. Do it first.

---

## Bottom line

AAA is not blocked by a wall we cannot climb. It is blocked by **three unsolved engineering and trust problems** that all get easier once the network has real operators, real reputation data, and real revenue.

Build F2P-first to solve trust, matching, and encoder quality at low stakes. AAA becomes available when Blockers 1 and 2 are answered — not when a lawyer signs something.
