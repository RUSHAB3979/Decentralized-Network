# Risk Register — Every Legal & Technical Threat, With Its Solution

**Date:** August 7, 2026
**Scope:** Complete threat map for the P2P compute + cloud gaming marketplace (India-first)
**Companion:** `SAFE-EXECUTION-PLAN.md` (the execution blueprint; cross-referenced as SEP §)
**Severity legend:** Critical (existential) · High (major damage) · Medium (contained damage)

**How to use this:** every risk has an ID, the concrete failure it describes, and a solution split into the control types that actually stop it — technical (code/infra), legal (paper), and process (habits). Review quarterly; add a row whenever a new feature ships.

---

## PART A — LEGAL & REGULATORY RISKS

### L-01 — Secondary copyright infringement
**Threat:** A title streams on the platform without rights; publisher claims you facilitated infringement. This is the claim that kills cloud-gaming startups.
**Solution:** *Technical:* `rights_basis` enforced as a hard filter in `matching.ts` — unlicensed titles cannot be scheduled, by code. *Legal:* only the four permitted rights bases (SEP §3.1); signed licenses archived in the Evidence Pack (SEP §8). *Process:* no-document-no-deployment rule; takedown drill quarterly.

### L-02 — Platform ToS breach / Valve or publisher shutdown
**Threat:** Steam SSA is personal, non-commercial; Valve or a publisher objects to your model and blocks it (the GeForce NOW 2020 precedent — publishers pulled catalogs even though users owned their games).
**Solution:** *Legal:* Steam PC Café Program membership + written clarification for the remote model; opt-in publisher consent before any BYOL title (SEP §3.3–3.4). *Process:* revenue diversification rule — compute track (no platform dependency) must be able to carry payroll alone, so a platform "no" is a setback, not a death.

### L-03 — Anti-circumvention violations (Copyright Act §65A / DMCA §1201)
**Threat:** Any DRM bypass, hardware-ID spoofing, or SSFN handling converts a civil gray zone into statutory violation territory.
**Solution:** *Technical:* clean images, genuine stable identifiers, no VM masking — verified by image signing so nobody "helpfully" patches this later. *Process:* the permanent red-line list (SEP §3.5); every rejected shortcut logged as a decision record.

### L-04 — Intermediary liability for illegal user workloads
**Threat:** A customer runs CSAM distribution, terror content, or attack tooling on a provider node; the state looks at the platform.
**Solution:** *Legal:* full IT Act §79 safe-harbor due diligence — published AUP, grievance officer, takedown timelines, actual-knowledge response (SEP §1.3); mandatory reporting of child-abuse material to authorities as required under Indian law. *Technical:* curated workload allowlist at launch, per-job egress deny-by-default, abuse-report → automatic job suspension. *Process:* takedown log with timestamps — the artifact that proves you acted properly.

### L-05 — DPDP Act non-compliance (rising to critical by mid-2027)
**Threat:** DPDP Rules were notified Nov 2025 with phased implementation: Consent Manager framework operational Nov 13, 2026, and full substantive compliance due May 13, 2027 — inside your launch window. Penalties scale to ₹250 crore per contravention, and security-safeguard and breach-notification failures sit in the highest bands.
**Solution:** *Technical:* data minimization already designed (hashed SteamID, no title tracking, ephemeral session data) — keep it; wire deletion-on-request into the database; breach-notification runbook with DPBI + user notification paths. *Legal:* standalone itemized privacy notice (separate from ToS), consent records, counsel review against the final Rules. *Process:* treat May 13, 2027 as a hard product deadline; assign one founder as privacy owner now.

### L-06 — Provider misclassification as employees
**Threat:** Providers argue they're employees (benefits, PF, termination protections); gig-economy classification suits are active territory in India.
**Solution:** *Legal:* Provider Agreement drafted for genuine independence — providers set availability, own their hardware, bear their costs, can serve competitors, paid per output not per hour of presence. *Process:* never issue schedules, quotas, or exclusivity demands; incentives yes, mandates no.

### L-07 — Consumer-protection claims for failed sessions
**Threat:** P2P sessions drop; a paying gamer files a consumer complaint over a ruined paid hour; consumer forums are cheap to invoke in India.
**Solution:** *Technical:* automatic session-credit refunds triggered by telemetry (session died → credit lands before the complaint exists). *Legal:* plain-language refund policy; no "no refunds" language (unenforceable and inflammatory). *Process:* grievance officer handles consumer complaints in the same ≤48h pipeline.

### L-08 — Payment-regulation breach (RBI)
**Threat:** Holding user funds or building custom payment flows walks into licensed-activity territory.
**Solution:** *Legal/Technical:* licensed payment aggregator for all collection and payouts; platform never custodies funds (SEP §1.6). *Process:* any new money feature (wallets, credits, escrow) gets counsel review before build — prepaid instruments are a separately regulated world.

### L-09 — Tax exposure (GST / TDS on marketplace payouts)
**Threat:** E-commerce operators have GST registration duties regardless of turnover and TDS deduction duties on provider payouts (§194-O regime); missed from payout #1, this compounds monthly.
**Solution:** *Process:* CA retained before first payout; deduction + filing automated in the payout pipeline; monthly compliance calendar. *Technical:* invoices and TDS records generated by the billing system, not by hand.

### L-10 — Money laundering / stolen-card abuse through compute purchases
**Threat:** Anonymous GPU-hours bought with stolen cards (classic pattern: card fraud → crypto mining); chargebacks plus regulator attention.
**Solution:** *Technical:* payment-verified accounts, velocity limits, mining banned in v1 AUP, anomaly flags on spend patterns. *Legal:* business KYC above monthly spend thresholds (SEP §4.3). *Process:* chargeback-rate monitoring with an auto-freeze rule.

### L-11 — Misclassification under real-money-gaming regimes
**Threat:** India's online gaming legislation targets money games; sloppy marketing ("win", "cash", tournaments) could drag the platform into a regime built to ban things.
**Solution:** *Legal:* counsel memo confirming the hardware-rental model sits outside money gaming; keep it current. *Process:* marketing language review rule — you rent GPUs; nobody wins money; no prize pools ever without fresh legal review (SEP §1.5).

### L-12 — Export-control / sanctions exposure on compute
**Threat:** Foreign customers use Indian GPU capacity from sanctioned jurisdictions or for restricted end-uses.
**Solution:** *Technical:* geo-blocking of sanctioned regions; customer-country capture at signup. *Legal:* counsel sizes the actual screening obligation (keep proportionate — you rent 4090s, not export supercomputers). *Process:* revisit when enterprise/foreign B2B begins.

### L-13 — Cross-border expansion compliance debt
**Threat:** Copy-pasting India compliance into SEA; each jurisdiction has its own data, gaming, payment, and tax regimes.
**Solution:** *Process:* per-country counsel before each launch (SEP Phase 4); expansion checklist template derived from this register; no "soft launches" in unreviewed jurisdictions.

### L-14 — User harmed on-platform sues (account ban, data loss)
**Threat:** A user's Steam account gets actioned after a session (anti-cheat false positive) and they blame — and sue — the platform.
**Solution:** *Technical:* anti-cheat whitelisting before BYOL titles go live; hostile-anticheat titles stay blocked (SEP §3.4). *Legal:* ToS acknowledgment of residual risk, liability cap, arbitration clause. *Process:* incident support path — help the user appeal with session evidence from the audit log; a supported user rarely becomes a plaintiff.

---

## PART B — TECHNICAL & SECURITY RISKS

### T-01 — Data theft from provider nodes
**Threat:** The core P2P fear: user session data, personal files, or compute inputs/outputs stolen from a stranger's machine — by malware on the host, a later renter, or disk forensics after the session.
**Solution:** *Technical:* per-session encrypted ephemeral volumes destroyed on exit; encryption keys held by the platform, never the host OS account; wipe-on-exit verified by the agent and spot-checked by random audit sessions (SEP §2.5); compute payloads decrypt only inside the sandbox. *Legal:* data-processing obligations in the Provider Agreement with indemnity. *Process:* wipe-verification failures auto-suspend the node pending investigation.

### T-02 — Provider snooping on live sessions
**Threat:** A malicious host screen-records or keylogs a user's session on their own hardware. Honest note: this is the hardest P2P risk to fully eliminate — physical access is powerful.
**Solution:** *Technical:* attested boot into the signed image (unauthorized capture software = failed attestation = no sessions); session pipeline isolated from the host user account; dedicated GPU per session. *Legal:* enumerated contract breach with bond forfeiture (SEP §2.5). *Process:* tier gating (only proven T1/T2 nodes host gaming), synthetic canary sessions that look like real users, and honest user-facing disclosure of the model. Residual risk exists; the mitigation stack makes it rare, costly, and career-ending for the provider.

### T-03 — Credential / OAuth-token theft
**Threat:** Steam tokens intercepted or replayed; a breach here is the "credential honeypot" scenario your AAA plan warns about.
**Solution:** *Technical:* QR/device-code flow only (password never exists anywhere in your system); minimal OAuth scopes; tokens short-lived, encrypted in transit, revoked at session end; zero at-rest storage beyond session lifetime. *Process:* quarterly verification that no code path logs or persists tokens — grep the codebase, check the log sinks.

### T-04 — Malicious workload escapes the sandbox
**Threat:** A compute job breaks isolation and owns the provider's machine — the incident that would destroy provider-side trust permanently.
**Solution:** *Technical:* gVisor/Firecracker isolation, no privileged containers, no host mounts, syscall filtering, hard resource caps, GPU passthrough only to the sandbox; curated-image allowlist in v1 so hostile code never arrives (SEP §4.1–4.2). *Process:* external pen-test before Phase 1 exit; patch SLA on runtime CVEs (48h); vulnerability-disclosure program.

### T-05 — Tampered provider agent / forged telemetry
**Threat:** A provider modifies the agent to fake capabilities, inflate metrics, or bill for phantom sessions.
**Solution:** *Technical:* signed agent binaries (unsigned = refused), TPM attestation for gaming tiers, orchestrator-side cross-checks (claimed RTT vs. independently measured RTT; claimed GPU vs. benchmark canary jobs). *Legal:* enumerated fraud breach → bond forfeiture + termination. *Process:* statistical outlier review of telemetry weekly.

### T-06 — Man-in-the-middle on streams and control plane
**Threat:** Session video/input or orchestrator commands intercepted or altered in transit.
**Solution:** *Technical:* WebRTC's mandatory DTLS-SRTP for media; mTLS with per-node client certificates for agent↔orchestrator (SEP §5); certificate pinning in the agent; TLS everywhere on the API. **Process:** TLS config scanned in CI; no plaintext fallback paths, ever.

### T-07 — Orchestrator compromise (the crown jewels)
**Threat:** Whoever owns the orchestrator owns matching, payouts, and every session — single point of failure by design.
**Solution:** *Technical:* authn/authz on every endpoint (currently none — launch blocker), secrets in a vault not env files, least-privilege service accounts, dependency scanning, immutable audit log, tested backups. *Process:* incident-response runbook with severity levels and counsel-call criteria (SEP §5); founder 2FA on everything; production access audit monthly.

### T-08 — DDoS against the control plane
**Threat:** Matching API knocked offline; every live session orphaned; cheap attack, loud damage.
**Solution:** *Technical:* CDN/WAF in front of the orchestrator (Cloudflare-class), rate limiting per identity, queue backpressure (PLAN.md Phase 2), graceful session continuation when the control plane blips (data path is peer-to-peer — design so streams survive orchestrator downtime).

### T-09 — User account takeover
**Threat:** Weak user auth → stolen accounts → fraudulent sessions billed to victims.
**Solution:** *Technical:* strong password policy + TOTP 2FA, login-anomaly detection, session invalidation on password change, payment re-verification for new devices. *Process:* support flow for compromise reports with immediate freeze.

### T-10 — Sybil attacks on the reputation system
**Threat:** One operator spins up many fake provider identities to farm reputation, manipulate matching, or launder abuse across nodes.
**Solution:** *Technical:* KYC binds one legal identity to one provider account (SEP §2.1); device/hardware fingerprint dedup; graph analysis on payout accounts. *Process:* reputation earned only through completed, billed, audited sessions.

### T-11 — Residual data in VRAM / disk between tenants
**Threat:** Next renter recovers previous user's frame buffers or scratch data from GPU memory or unwiped disk.
**Solution:** *Technical:* GPU reset + VRAM scrub between sessions, ephemeral volume destruction, and pagefile wipe. *Process:* teardown checklist enforced by the agent and audited by canary sessions that plant and attempt to recover markers.

### T-12 — Supply-chain compromise (dependencies, build pipeline)
**Threat:** A poisoned npm/pip package or CI compromise ships malicious code inside your own signed agent — attestation then protects the attacker.
**Solution:** *Technical:* lockfiles committed, dependency pinning, automated vulnerability + integrity scanning in CI, signed reproducible builds, minimal dependency surface for the agent specifically. *Process:* review new dependencies like hires; the agent gets the strictest bar.

### T-13 — Outbound abuse from provider nodes
**Threat:** Workloads use provider IPs for spam, scanning, or attacks — providers get ISP-banned and blame the platform; platform IP reputation collapses.
**Solution:** *Technical:* per-job egress deny-by-default with declared-endpoint allowlists; SMTP and scan patterns always blocked (SEP §4.1); per-node abuse-complaint monitoring. *Legal:* AUP violation = customer termination; provider held harmless for platform-verified workloads.

### T-14 — Region/latency fraud by providers
**Threat:** Providers spoof region or VPN their location to capture better-paying matches, wrecking real latency for gamers.
**Solution:** *Technical:* multi-vantage RTT measurement (orchestrator + regional probes) overriding self-reported telemetry; IP-geo consistency checks; latency SLA enforcement per tier with automatic demotion.

---

## PART C — FRAUD, FINANCIAL & OPERATIONAL

### F-01 — Chargeback fraud spiral
**Solution:** payment-aggregator fraud tooling, velocity caps, session evidence (audit log) for representment, auto-freeze on chargeback-rate threshold.

### F-02 — Payout fraud (provider account hijack)
**Solution:** penny-drop verified bank accounts, payout-change cooldown + re-verification, 2FA on provider portal.

### F-03 — Insider risk (founder/employee access)
**Solution:** least-privilege from day one even at 5 people; production access logged; dual control on payout-system changes; vesting + IP assignment already in SEP §1.1.

### O-01 — Provider supply collapse (the marketplace cold-start)
**Solution:** weekly payouts, transparent earnings dashboard, the §2.6 provider-protection promises, LAN-café and mining-rig partnership channel, compute demand as the utilization floor that keeps provider earnings real.

### O-02 — Key-person and knowledge concentration
**Solution:** runbooks for every operational task, documented infrastructure-as-code, no single founder holding sole access to payments, DNS, or production.

### O-03 — Insurance gaps discovered during a claim
**Solution:** cyber + E&O policies purchased against this register; annual coverage review as the platform's risk surface grows.

---

## REVIEW CADENCE

| Trigger | Action |
|---|---|
| Quarterly | Full register review; severity re-scoring; new-feature risks added |
| New feature touching money, data, or third-party content | Pre-launch register entry + counsel check if legal-adjacent |
| Any incident | Post-mortem adds/updates a register entry with the control that failed |
| New jurisdiction | Fork Part A per L-13 before launch |

**The one-line summary of this entire document:** every risk above is survivable if it has an owner, a control, and a paper trail — and fatal only when it's a surprise. Keep the register alive and nothing on this list gets to be a surprise.
