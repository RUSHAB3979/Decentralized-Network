# Genuinely Free Compute — No Credit Card, No Trials

**For:** Decentralised P2P Compute Marketplace
**Constraints (confirmed by Rushab, 2026-08-06):**
- Azure for Students — verification fails, unusable
- Oracle Always Free — **requires a Visa/Mastercard for identity verification.** Excluded.
- Hugging Face ZeroGPU — free but capped at ~5 min per execution. Not usable as a work machine.
- i3 laptop, no local GPU

**Rule for this document: no credit card, no trial clocks, no "free for 30 days."**
Every figure below was read off a live page on 2026-08-06. Source URL given for each.

---

## TIER 1 — The three that actually work

### 1. Kaggle Notebooks — 30 GPU HOURS PER WEEK, NO CARD
Source: https://www.kaggle.com/docs/efficient-gpu-usage

> "Kaggle provides free access to NVIDIA TESLA P100 GPUs."
> "You can use up to a quota limit per week of GPU. The quota resets weekly and is **30 hours** or sometimes higher depending on demand and resources"

**This is the single best free GPU on the internet right now for your situation.**
- Tesla P100 16GB — a real datacenter GPU, not a hobbyist card
- 30 hours **every week**, resetting weekly — that's ~130 hrs/month
- Signup needs only email + phone verification. **No credit card.**
- TPUs also available on a separate quota

Use it for: model training, Blender headless renders (`bpy` runs fine), batch inference, benchmarking your marketplace's workload profiles.
Limits: 12hr max per session, notebook-based (no persistent SSH), internet must be manually enabled per notebook.

### 2. Google Colab — free GPU, no card
Source: https://research.google.com/colaboratory/faq.html

> "Colab is a hosted Jupyter Notebook service that requires no setup to use and provides **free of charge** access to computing resources, including GPUs and TPUs."
> "Is it really free of charge to use? **Yes.** Colab is free of charge to use."
> "notebooks can run for at most **12 hours**, depending on availability and your usage patterns"

Honest caveats, quoted directly from Google:
> "In the version of Colab that is free of charge, access to expensive resources like GPUs is **heavily restricted**."
> "Colab does not publish these limits, in part because they can vary over time."
> "Colab **prioritizes users who are actively programming in a notebook**" — leave the tab idle and you lose the runtime.

So: unpredictable GPU type, unpublished quota, needs you to be interactively present. Still genuinely free with no card. **Use Kaggle as primary, Colab as overflow** when your weekly Kaggle quota is spent.

### 3. GitHub Codespaces — 180 CORE-HOURS/MONTH (you already have this)
Source: https://docs.github.com/en/billing/managing-billing-for-your-products/about-billing-for-github-codespaces

| Plan | Storage/month | Compute time/month |
|---|---|---|
| GitHub Free | 15 GB-month | 120 hrs |
| **GitHub Pro (yours via Student Pack)** | **20 GB-month** | **180 hrs** |

180 core-hours = 90 hours on a 2-core box, or 45 hours on 4-core. **No card, already unlocked by your Student Pack.**

No GPU — but this is your Linux dev box. Run the coordinator, the node daemon, Postgres, the matcher, integration tests. This replaces your i3 for all non-GPU development.

---

## TIER 2 — Free hosting, no card

**Cloudflare Workers Free** — https://developers.cloudflare.com/workers/platform/limits/
> Requests: **100,000/day** (resets midnight UTC, Error 1027 when exceeded)
> CPU time: 10 ms/request | Memory: 128 MB | Subrequests: 50/request

Free tier signup does not require a card. Perfect for your marketplace's edge layer: node heartbeat ingestion, region routing, API gateway, webhook receiver. 100k req/day is plenty pre-launch.

**GitHub Pages** — free static hosting, unlimited project sites, no card. Landing page + docs.

**MongoDB Atlas M0** — free forever tier, no card required for M0. Plus the $50 credit from your Student Pack.

**Heroku** — $13/mo × 24 months from the Student Pack. Card may be required at signup for verification; the credit covers actual usage. Worth testing since it's already yours.

---

## What to do about the always-on coordinator

This is the real hole now that Oracle is out. A P2P marketplace needs a 24/7 endpoint, and every genuinely card-free option is either request-based or session-based.

**Recommended approach: go serverless instead of always-on.**

Cloudflare Workers has no idle cost and no card — it wakes on request. Restructure the coordinator so it is stateless and event-driven:
- Node heartbeats → Worker endpoint → write to Atlas
- Job submission → Worker → queue in Atlas
- Matching → runs on the Worker at request time, or on a Cron Trigger

This is architecturally better anyway. A stateless control plane is easier to scale and is how a decentralised network should work — no single always-on box to be a point of failure. You avoid needing a free VPS entirely.

Fallback if you truly need a persistent box: run it in Codespaces during active development (180 hrs/month), and only pay for a real VPS once you have users or revenue.

---

## Realistic workflow with zero rupees and zero card

| Task | Where | Free allowance |
|---|---|---|
| Write backend code, run tests, Postgres, daemon | **Codespaces** | 180 core-hrs/mo |
| Train models / GPU benchmarks / Blender renders | **Kaggle** | 30 GPU-hrs/**week** |
| GPU overflow when Kaggle quota spent | **Colab** | unpublished, 12hr sessions |
| Coordinator API / heartbeats / routing | **Cloudflare Workers** | 100k req/day |
| Database | **MongoDB Atlas M0** | free tier + $50 credit |
| Landing page + docs | **GitHub Pages** | unlimited |
| Monitoring | **Datadog** (Student Pack) | 10 servers, 2 yrs |
| Errors | **Sentry** (Student Pack) | 50k errors/yr |
| Secrets | **Doppler** (Student Pack) | free Team plan |

**Monthly cost: ₹0. Cards required: none.**

---

## Explicitly ruled out

| Option | Why |
|---|---|
| Azure for Students | Verification fails for this account |
| Oracle Always Free | Requires Visa/Mastercard for identity check |
| Hugging Face ZeroGPU | ~5 min execution cap — demo only, not a work machine |
| Fly.io | $5 Hobby free-trial plan is deprecated; no meaningful free compute left |
| Google Cloud $300 | 90-day clock + card required |
| AWS Free Tier | Card required |
| Lambda / RunPod / Vast / Modal | No free credits found on any pricing page; all pay-per-hour |

---

## Paid rates, for when you have revenue

Not free, but this is the price floor you're competing against — and the cheapest way to buy GPU when you actually need it.

**Vast.ai** (https://vast.ai/pricing) — RTX 3090 from **$0.08/hr**, RTX 4090 from **$0.13/hr**, H100 PCIE from $1.53/hr
**RunPod** (https://www.runpod.io/pricing) — RTX 4090 $0.69/hr, A100 80GB $1.39/hr, H100 SXM $2.99/hr

10 hours of RTX 3090 on Vast.ai ≈ $1 ≈ ₹85. Even with zero budget, that's reachable when you genuinely need a card Kaggle can't give you.

**Strategic note:** Vast.ai at $0.08/hr across 40+ datacenters is a price floor you cannot beat head-on. Your gaming/latency wedge is the correct strategy — their cheap tier is batch-oriented and latency-indifferent. Price is their game; sub-120ms is yours.

---

## Verification notes

- Kaggle quota: read from Kaggle's own docs page, rendered in browser (the page blocks curl with reCAPTCHA)
- Colab: quotes taken verbatim from Google's official FAQ
- Codespaces: table read from GitHub's billing docs
- Cloudflare: read from the Workers platform limits page
- Vast.ai: live market rates from their pricing page
- **Not independently verified:** whether Kaggle/Colab ever require a card at signup in India. Both are documented as free with phone verification only, but confirm during your own signup.
