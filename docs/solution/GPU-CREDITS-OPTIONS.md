> **SUPERSEDED IN PART — see `FREE-COMPUTE-NO-CARD.md`**
> Two recommendations in this document do not survive contact with reality:
> - **Oracle Always Free** requires a Visa/Mastercard for identity verification → unusable
> - **Hugging Face ZeroGPU** is capped at ~5 min per execution → demo only, not a work machine
>
> This file is retained for its verified GPU *rental* price tables and competitive intel.
> For genuinely free, no-card compute, read `FREE-COMPUTE-NO-CARD.md` instead.

# GPU & Cloud Compute — Verified Options (No Azure)

**For:** Decentralised P2P Compute Marketplace
**Constraint:** i3 laptop, no local GPU. Azure for Students verification fails — excluded.
**Verification date:** 2026-08-06
**Method:** Every number below was read off a live page loaded at the time of writing. Source URL given for each. Nothing here is recalled from memory.

---

## The headline: there is ONE genuinely free, always-on option

**Oracle Cloud Always Free — ARM Ampere A1**
> "All tenancies get the first 1,500 OCPU hours and 9,000 GB hours per month for free for VM instances using the VM.Standard.A1.Flex shape"
> Plus 200 GB Always Free block volume storage.
> Source: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm

**Why this is the single most important entry in this document:**
1,500 OCPU-hours/month ≈ **4 ARM cores running 24/7, forever, at zero cost.** Not a trial. Not 30 days. Always Free.

For a P2P compute marketplace this is exactly the right shape for your **coordinator / control plane**: the always-on node registry, job queue, matcher, and heartbeat listener. That component needs uptime, not GPU. Oracle gives you production-grade uptime for free, permanently.

Caveats (stated on the page): capacity limits apply per region — A1 instances are frequently unavailable in popular regions and you may need to retry signup or pick a different AD. Also "One Oracle Cloud Free Trial or Always Free account is permitted per person."

Separately, Oracle gives **US$300 credit for 30 days** on signup (source: https://www.oracle.com/cloud/free/) — short window, so don't waste it; use it deliberately for a burst test.

---

## GPU rental — real hourly prices (no free GPU credits found anywhere)

**Important honest finding: none of the GPU providers below advertise a free credit or student GPU grant on their public pricing pages.** I checked. The RunPod pricing page has no "free credit" text on it at all. If you saw a $10/$25/$50 free-credit claim somewhere, treat it as expired promo copy until you see it in your own signup flow.

### Vast.ai — cheapest, marketplace model (live spot rates)
Source: https://vast.ai/pricing — "Prices set by supply and demand across 40+ data centers"

| GPU | VRAM | From | Median |
|---|---|---|---|
| RTX 3090 | 24GB | **$0.08/hr** | $0.15/hr |
| RTX 4090 | 24GB | **$0.13/hr** | $0.36/hr |
| RTX 5090 | 32GB | $0.16/hr | $0.45/hr |
| L4 | 24GB | $0.06/hr | $0.33/hr |
| L40S | 48GB | $0.40/hr | $0.53/hr |
| RTX PRO 6000 WS | 96GB | $0.53/hr | $1.18/hr |
| H100 PCIE | 80GB | $1.53/hr | $2.13/hr |
| H100 SXM | 80GB | $1.60/hr | $2.52/hr |
| H200 | 141GB | $2.63/hr | $4.15/hr |
| B200 | 192GB | $5.00/hr | $5.88/hr |

**Also: Vast.ai is your closest direct competitor and it publishes its full price book.** This table is competitive intelligence, not just a shopping list — it is the price floor you have to undercut or out-differentiate.

### RunPod — more reliable, higher floor
Source: https://www.runpod.io/pricing

| GPU | VRAM | Price |
|---|---|---|
| RTX A5000 | 24GB | $0.27/hr |
| A40 | 48GB | $0.44/hr |
| RTX 3090 | 24GB | $0.50/hr |
| RTX A6000 | 48GB | $0.53/hr |
| **RTX 4090** | 24GB | **$0.69/hr** |
| L40 | 48GB | $0.82/hr |
| RTX 6000 Ada | 48GB | $0.84/hr |
| L40S / RTX 5090 | 48/32GB | $0.99/hr |
| A100 PCIe | 80GB | $1.39/hr |
| A100 SXM | 80GB | $1.49/hr |
| RTX Pro 6000 | 96GB | $1.99/hr |
| H100 PCIe | 80GB | $2.89/hr |
| H100 SXM | 80GB | $2.99/hr |
| H100 NVL | 94GB | $3.19/hr |
| H200 | 141GB | $4.39/hr |
| B200 | 180GB | $5.89/hr |

### Lambda — enterprise tier, most expensive
Source: https://lambda.ai/service/gpu-cloud (price per GPU per hour, plus applicable taxes)

| GPU | VRAM | Price/GPU/hr |
|---|---|---|
| Tesla V100 | 16GB | $0.79 |
| A6000 | 48GB | $1.09 |
| A100 PCIe / SXM 40GB | 40GB | $1.99 |
| A100 SXM | 80GB | $2.79 |
| H100 SXM | 80GB | $3.99–$4.19 |
| B200 SXM6 | 180GB | $6.69–$6.89 |

No free tier or student offer found on the page.

### Modal — serverless, per-second billing
Source: https://modal.com/pricing

| GPU | Per second | ≈ Per hour |
|---|---|---|
| Nvidia L4 | $0.000222 | ~$0.80 |
| Nvidia A10 | $0.000306 | ~$1.10 |
| Nvidia L40S | $0.000542 | ~$1.95 |
| A100 40GB | $0.000583 | ~$2.10 |
| A100 80GB | $0.000694 | ~$2.50 |
| RTX PRO 6000 | $0.000842 | ~$3.03 |
| H100 | $0.001097 | ~$3.95 |
| H200 | $0.001261 | ~$4.54 |
| B200 | $0.001736 | ~$6.25 |
| B300 | $0.001972 | ~$7.10 |

Hourly figures are my arithmetic (rate × 3600), not quoted by Modal. Per-second billing means you pay nothing while idle — good for bursty inference, bad value for long training runs. I could not confirm a specific free monthly credit figure from the pricing page.

---

## Free GPU that actually exists (with strings)

**Hugging Face ZeroGPU — FREE**
Source: https://huggingface.co/pricing
> "ZeroGPU | dynamic | Nvidia RTX Pro 6000 Blackwell | up to 96 GB | **FREE**"

Free-tier Spaces hardware table also confirms:
- CPU Basic: 2 vCPU, 16GB — FREE
- CPU Upgrade: 8 vCPU, 32GB — $0.03/hr
- Nvidia T4 small: 16GB — $0.40/hr
- Nvidia T4 medium: 16GB — $0.60/hr

**This is a real free GPU with a 96GB Blackwell card behind it.** It is quota'd and queued (HF Pro at $9/mo gives "8× ZeroGPU quota and highest queue priority"), and it only runs inside a Gradio/Docker Space — you cannot SSH into it. But for hosting a public demo of your AI/3D generation pipeline, it costs zero.

---

## Supporting infrastructure (free tiers, verified)

**Google Cloud** — https://cloud.google.com/free/docs/free-cloud-features
> "$300 Welcome credit to spend over 90 days"; Free Tier products continue up to monthly limits after. Credit card required for signup verification.

**Cloudflare Workers Free** — https://developers.cloudflare.com/workers/platform/limits/
> Requests: **100,000/day**, resetting midnight UTC (Error 1027 when exceeded)
> CPU time: 10 ms per request | Memory: 128 MB | Subrequests: 50/request

Ideal for the lightweight edge layer of your marketplace: node heartbeat ingestion, region routing, API gateway. 100k requests/day free is generous for pre-launch.

**Fly.io** — https://fly.io/docs/about/pricing/
> The old $5/month Hobby plan with free trial credit is **deprecated**. Current model is Pay As You Go.
> Still free: all inbound data transfer; data transfer between apps/Machines in the same region; first 10GB/month of volume storage; first 10 single-hostname certificates per org.
> **There is no meaningful free compute allowance on Fly.io anymore.** Don't plan around one.

---

## Recommended stack for the marketplace (zero to near-zero cost)

| Layer | Use | Cost |
|---|---|---|
| Coordinator / control plane | **Oracle Ampere A1 Always Free** (4 cores, 24/7) | $0 forever |
| Edge API / heartbeat ingest | **Cloudflare Workers** (100k req/day) | $0 |
| Database | **MongoDB Atlas** ($50 credit from GitHub pack + M0 free) | $0 |
| Backup app hosting | **Heroku** ($13/mo × 24 from GitHub pack) | $0 (pack) |
| Dev environment | **GitHub Codespaces Pro** (from pack) | $0 (pack) |
| Monitoring | **Datadog** 10 servers 2yr + **Sentry** (from pack) | $0 (pack) |
| Public AI demo | **Hugging Face ZeroGPU Space** | $0 |
| GPU burst testing | **Vast.ai RTX 3090 @ $0.08–0.15/hr** | ~$1–2 for 10hrs |
| Serious training run | **RunPod A100 80GB @ $1.39/hr** | pay per use |

**Total fixed monthly cost: $0.** GPU spend is purely on-demand.

---

## Strategic note for the startup itself

Vast.ai's public price book (RTX 3090 from $0.08/hr, RTX 4090 from $0.13/hr) is the number your marketplace must beat or sidestep. Competing on raw price against a 40-datacenter spot market is not winnable from a standing start.

Your stated moat — encoder support, region-aware matching, sub-120ms latency for the **gaming** track — is the right call precisely because Vast.ai's cheap tier is batch-oriented and latency-indifferent. Price is their game; latency is yours. Keep the gaming track as the wedge.

---

## What I could not verify

- **No free-credit promos confirmed** for Lambda, RunPod, Vast.ai, or Modal. Their pricing pages carry no such offer text. Any specific dollar figure you see quoted elsewhere should be confirmed inside the actual signup flow before you rely on it.
- **Modal's free monthly compute allowance** — not stated on the pricing page I loaded.
- **AWS Activate credits** — not checked in this pass; worth a look later since Activate can be worth $1k–$5k for incorporated startups, but eligibility usually needs incorporation or accelerator affiliation.
- **India-region availability** for Oracle A1 free tier — capacity is explicitly limited and varies; you'll only find out at signup.
