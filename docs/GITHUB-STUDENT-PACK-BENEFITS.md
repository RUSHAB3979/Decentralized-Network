# GitHub Student Developer Pack — What To Actually Claim

**For:** Decentralised P2P Compute Marketplace
**Status:** Pack membership already active
**Source:** https://education.github.com/pack (84 offers parsed from the live page)
**Note:** Every offer text below is quoted from the live pack page, not from memory.

---

## TIER 1 — Claim today, these directly serve the startup

| Offer | What you get (exact wording from pack page) | Why it matters here |
|---|---|---|
| **GitHub Pro** | "Free GitHub Pro while you are a student." | Unlimited private repos + more Actions minutes. Your control-plane repo stays private until launch. |
| **GitHub Codespaces** | "Free Pro level access to Codespaces to use anywhere in your account." | **Biggest one for you.** i3 laptop with no GPU → Codespaces gives you a real Linux dev box in the cloud. Run the node daemon, matcher, and API server there instead of locally. |
| **Heroku** | "$13 USD per month for 24 months." | ~$312 total. Enough to host the coordinator/control-plane API continuously for 2 years. Free-tier dynos are gone, this credit replaces them. |
| **MongoDB Atlas** | "$50 in MongoDB Atlas Credits, plus MongoDB Compass and MongoDB University including free certification valued at $150." | Node registry, job queue, reputation records. Atlas free M0 tier + $50 credit covers you well past MVP. |
| **Datadog** | "Pro Account, including 10 servers. Free for 2 years." | Monitor 10 provider nodes free. Latency/GPU-util dashboards are exactly what you need to prove the <120ms claim vs GPUnity. |
| **Sentry** | "50K errors, 100K transactions, 1GB attachments, 500 replays, Team features, 1 yr (renewable)." | Error tracking across distributed nodes. Critical when nodes fail in the wild and you can't reproduce locally. |
| **New Relic** | "Free New Relic while you are a student. ($300/month value)" | Alternative/complement to Datadog. Full APM. |
| **Doppler** | "Free Doppler Team subscription while the user is an active student." | Secrets management across nodes. Do NOT hardcode node keys — this solves it properly and free. |
| **Termius** | "Free access to all Termius Pro and Termius Team features." | SSH into provider nodes from desktop AND phone, synced. You'll be debugging nodes constantly. |
| **Stripe** | "Waived transaction fees on first $1000 in revenue processed." | Direct money: your first ~$1000 of marketplace revenue is fee-free. Claim before you take a single payment. |
| **Clerk** | "Free Pro plan while you're a student." | Auth + user management + billing for the marketplace. Saves weeks of building auth yourself. |

---

## TIER 2 — Claim soon, high value

| Offer | What you get | Use for |
|---|---|---|
| **JetBrains** | "Free subscription for students, renewed annually." | PyCharm/GoLand/WebStorm full versions. |
| **1Password** | "Free for a year including 1Password Developer Tools." | Credential vault, SSH agent. |
| **Namecheap** | "1 year .me domain + 1 SSL cert free for 1 year." | Grab a domain. |
| **.TECH** | "One standard .TECH domain free for 1 year." | Better fit than .me for a compute startup. |
| **Name.com** | "Free domain, 25+ extensions incl. .live, .studio, .software, .app, .dev" | **Best of the three** — `.dev` or `.app` reads far more credible than `.me`. |
| **Appwrite** | "Education plan, 2 projects with Appwrite Pro resource limits, worth $40/month." | Open-source BaaS. Realistic alternative to writing all your own backend plumbing. |
| **GitHub Pages** | "One site per account/org, unlimited project sites." | Free landing page + docs site. |
| **LocalStack** | "Free license to LocalStack's most powerful AWS emulator." | Emulate S3/SQS locally — test the job-distribution layer without paying AWS. |
| **Codecov** | "Free on public and private repositories." | Coverage gates on the matcher/scheduler logic. |
| **Travis CI** | "Private builds for free while you're a student." | Backup CI if you exhaust Actions minutes. |
| **ConfigCat** / **DevCycle** | "1000 feature flags, ∞ users free" / "1 free year Starter, unlimited flags & usage." | Ship features to a subset of provider nodes safely. |
| **SimpleAnalytics** | "Starter plan free for one year, 100k page views/month." | Privacy-friendly analytics on the landing page. |
| **Requestly** | "Professional plan (worth $270) free for one year." | Intercept/mock HTTP — very useful debugging node↔coordinator protocol. |
| **Honeybadger** | "Free Small account for 1 year." | Uptime + cron monitoring for the coordinator. |
| **PopSQL** / **SQLGate** | Free Premium / Standard features for 1 year. | SQL client if you go Postgres for billing records. |
| **Blockchair** | "100,000 free requests." | Only if you add a crypto/token settlement layer. Multi-chain API. |
| **Camber** | "200 CPU hours, 75GB storage, 200 LLM messages per month." | Free scientific-compute CPU hours. Useful for benchmarking batch workloads. |

---

## TIER 3 — Learning & career (your AI-engineer / DSA goals)

| Offer | What you get |
|---|---|
| **DataCamp** | 3 months free access |
| **Educative** | 6 months free, 70+ courses (Web Dev, Python, Java, ML) |
| **FrontendMasters** | 6 months free, all courses and workshops |
| **Scrimba** | Interactive frontend courses |
| **Boot.dev** | Backend/devops curriculum (Python, Go, TypeScript) |
| **Codédex** | Beginner-friendly Python/JS/React |
| **AlgoExpert** | 20 free coding-interview questions + 10% off — **relevant to your DSA / high-LPA fallback goal** |
| **InterviewCake** | Full interview prep course for 1 week (time-box this one) |
| **GitHub Foundations Certification** | Free cert exam prep + voucher path |

---

## Explicitly NOT recommended

| Offer | Why not |
|---|---|
| **Microsoft Azure ($100 credit, 25+ services)** | Listed on the pack and looks great on paper, but **verification does not work for this account** — confirmed failure. Do not burn more time on it. |
| **Microsoft Azure for ages 13-17** | Age-gated, not applicable. |
| **Visual Studio Dev Essentials ($200 Azure credit)** | Same Azure dependency. Only worth retrying if Azure verification is ever fixed. |
| **GitHub Copilot** | Pack page currently states: *"New plan sign-ups are temporarily paused as we ensure a high-quality experience."* Check back later; not claimable right now. |

---

## The gap the pack does NOT fill

**No GPU compute.** Nothing in the 84 offers gives you GPU hours (Camber is CPU-only, Azure is blocked for you).
For a compute marketplace this is the critical missing piece — see `GPU-CREDITS-OPTIONS.md` for verified external options.

---

## Claim order (do it in this sequence)

1. GitHub Pro + Codespaces — unblocks development immediately on the i3 laptop
2. Name.com domain (.dev or .app) — grab the name before someone else does
3. Heroku ($13/mo × 24) — stand up the coordinator API
4. MongoDB Atlas ($50) — node registry + job queue
5. Doppler — secrets, before you write any node auth code
6. Datadog + Sentry — instrument from day one, not after launch
7. Termius — you'll want mobile SSH the first time a node dies at 2am
8. Stripe — before first revenue, so the fee waiver isn't wasted
9. Everything in Tier 2 as needed

All offers: https://education.github.com/pack
