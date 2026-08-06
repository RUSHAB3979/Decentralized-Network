# The Way Through — Legal Paths That Are Actually Open

**For:** Decentralised P2P Cloud Gaming Marketplace
**Verified:** 2026-08-06, all quotes from live pages
**Purpose:** Section 5b established that Steam Cloud Play is provider-whitelisted and closed to us. This document finds the doors that are open.

---

## THE BIG FIND: Steam PC Café Program

Source: https://partner.steamgames.com/pccafe

**Valve operates a commercial licensing program.** It is public, has a sign-up page, and exists precisely to let a business let *other people* play games on hardware the business controls. This is the commercial-use permission the Subscriber Agreement says you must have.

Valve's own words:

> "Bring the ultimate gaming platform into your establishment or entertainment space with Steam PC Café. Offering a growing library of **commercially-licensed** Steam and SteamVR titles, and a robust set of tools to manage them"

> "the Steam PC Café program can help power up any kind of gaming space—**ranging from school clubs to internet cafés, and everything in between**"

### The two features that matter enormously

**1. Floating Licenses — this is the whole ballgame**

> "**Floating Licenses** — Use a single Steam account to purchase additional game licenses and **share them with visitors—customers or guests alike**—via your local network. The entire Steam experience is just a few clicks away."

Read that again. This is *explicit written permission* to buy licences on one account and let visitors play them. It is the exact thing the SSA otherwise forbids ("not entitled to... rent, lease or license the Content to others **without the prior written consent of Valve**"). The Café program **is** that written consent, productised.

**2. Local Content Cache — solves your download problem**

> "**Local Content Cache** — Games and updates only need to be **downloaded once before everyone on the local network can access them** without further impact to Internet bandwidth."

Valve themselves built the "download once, serve many" model you wanted. Officially sanctioned, in-product.

**Plus multi-site support:**

> "**Multi-Location Support** — If your organization operates from multiple locations, you can identify each site during the registration process and **share all of your Steam content across all of your sites**."

A distributed network of physical locations sharing one licence pool. That is structurally very close to what you are building.

### The honest caveats

- The program is oriented to **physical venues on a local network** — cafés, school clubs, esports lounges. It is not written for streaming to a remote consumer over the internet, and the "local network" language matters.
- Only titles whose publishers joined the café catalogue are available ("a growing library"), not all of Steam.
- Requirements/FAQ/sign-up pages sit behind a Steamworks login, so exact fees, country eligibility (India especially) and contract terms are **unverified** — these must be read after signing in.
- Whether Valve permits *remote* streaming from a café-licensed machine is **the single question to ask them**. Do not assume yes.

### Why this changes the picture anyway

Even under the strictest reading, this is the first *public, self-serve* commercial licensing door found so far — no "we'll reach out to you" gatekeeping. And it points directly at a viable first business (below).

**Action: create a Steamworks account, sign in, read `/pccafe/requirements`, `/pccafe/faq`, `/pccafe/signup`, and email Valve the remote-streaming question directly.**

---

## PATH 2: The Shadow model — rent the whole PC, not the game

Source: https://shadow.tech/en-GB/shadow-pc

Shadow rents a full cloud Windows PC:

> "It's a PC but better — For office work, demanding creative projects or development, **easily install your favorite software** on your Shadow Pro powerful Cloud Workstation."

> "Your high-performance Windows PC, accessible from your Mac"

**Why this is legally different from GFN:** Shadow doesn't run a game catalogue. They rent you a computer. *You* install your own software under your own licences, exactly as you would on a laptop you bought. Shadow never touches the licence chain — so they never needed Valve's permission, and they are not on the Steam Cloud Play whitelist.

**This is the model with no whitelist in front of it.** Renting computing hardware is not licensing games.

**For our P2P network this means:** frame the product as *renting a remote Windows desktop* — the operator supplies hardware, the renter installs their own software under their own licences and gets exclusive, isolated use of that machine for the session.

**Caveats, stated plainly:**
- Shadow is a single company operating its own datacenters with dedicated per-user VMs. Our supply side is strangers' home PCs — a materially different trust and isolation story.
- The SSA's "personal, non-commercial use" clause applies to the *player's* licence. A player installing their own game on rented hardware for their own play is a much stronger position than an operator renting out their copy — but it is not risk-free, and EULAs vary by publisher.
- This model implies **full-session exclusivity and a clean wipe**, not shared access to an operator's installed library.

---

## PATH 3: F2P + Indie (unchanged, still the fastest start)

Covered in `GAME-LICENSING-PROBLEM.md` sections 4 and 5b. No licence to transfer, pre-install is legal, cache-sharing between nodes is legal, huge Indian market, maximum latency sensitivity. **This remains the launch wedge.**

---

## RECOMMENDED STRATEGY — sequenced, each stage funds the next

### Stage 1 (now, zero permission needed): F2P + own-IP + batch compute
Build the full stack — node daemon, region-aware matcher, encoder pipeline, cache-warm scoring, ephemeral sessions. Launch on BGMI/Valorant/Genshin-class F2P titles and Blender/render batch jobs. Prove sub-120ms in India with real players on friends' RTX machines. **No licence gate exists here.**

### Stage 2 (weeks 2–8, cheap and high-information): talk to Valve
Sign in to Steamworks, read the café requirements/FAQ, and ask Valve directly:
1. Can a PC Café licence cover machines players access remotely?
2. What are the India eligibility terms and fees?
3. What is the path for a new provider to be considered for Steam Cloud Play?

Cost: an email. Potential upside: a legitimate, *public* commercial licence path that no P2P competitor is using. Most startups never even ask.

### Stage 3 (months 2–6): indie catalogue via written consent
Valve's SSA anticipates "prior written consent." Indie studios can grant it for their own IP directly. Sign them one at a time — this builds a defensible paid catalogue that Vast.ai and io.net structurally cannot copy, because they have no gaming relationships at all.

### Stage 4 (months 6+): position as desktop rental (Shadow model) for paid titles
Once operators are KYC'd, bonded, and sessions are hardware-isolated with clean wipes, the "rent a remote PC, bring your own software" framing becomes defensible. Requires real legal review before launch — but it needs no whitelist.

---

## What this means for the dream

The AAA-on-day-one version is genuinely closed — Valve gatekeeps that and NVIDIA needed a corporate partnership to get in. That is not a reflection on the idea or the engineering.

But **three separate doors are open right now**, and one of them (PC Café) is a public commercial licensing program with explicit floating-licence permission that most people building in this space have never read.

The correct move is not to abandon the plan. It is to **launch on the open doors, build the real product, and negotiate the closed ones from a position of having actual users and traffic.** Valve, and indie studios, respond to working products with players — not to pitch decks from pre-launch startups.

Nothing here requires abandoning the moat: encoder support, region-aware matching, cache-warm scheduling and dual-track supply are all still exactly right. Only the *initial catalogue* changes.

---

## Open questions (must verify before relying on any of this)

- PC Café: fees, India eligibility, and whether remote streaming is permitted — all behind Steamworks login, **unverified**
- Which publishers participate in the café catalogue
- Anti-cheat behaviour (Vanguard/BattlEye/EAC) on remote and virtualised machines — could constrain the F2P wedge, test early
- Indian IT Act intermediary liability for a marketplace operator
- Credential isolation on untrusted nodes — still the hardest unsolved trust problem; needs its own threat model
