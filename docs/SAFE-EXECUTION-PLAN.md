# Safe Execution Plan — P2P Compute Marketplace (India-First)

**Date:** August 7, 2026  
**Scope:** Legal, platform, provider, and revenue controls for the P2P compute and cloud-gaming marketplace.  
**Companion:** [RISK-REGISTER.md](RISK-REGISTER.md)

> This is an engineering operating blueprint, not legal or tax advice. Retained Indian technology counsel and a CA must confirm the legal, payment, tax, and data-protection details before reliance.

## Operating premise

Zero legal risk is impossible. The launch standard is **permission-based operation**: a written permission, signed agreement, or official program membership for every activity; KYC-verified, contracted, attested providers; logged revocable consent; and auditable evidence.

**Non-negotiable:** if a title, workload, or provider cannot be pointed to a permitting document, it does not run. No launch exception.

| Do not operate on | Operate on |
|---|---|
| Tolerated grey-zone activity | Written permission, signed license, or official program membership |
| Anonymous providers | KYC-verified, contracted, bonded, attested providers |
| Implied consent | Explicit, logged, revocable consent |
| Hope | Insurance, indemnity, safe-harbor compliance, and an audit trail |

## Layer 1 — Corporate and legal foundation (weeks 0–6)

Before an external provider or customer is onboarded:

1. Incorporate an Indian Private Limited company; execute four-year vesting / one-year cliff founder agreements and IP assignments; separate company and personal funds; register GST as required.
2. Retain Indian counsel for: user ToS (hardware-rental framing), Provider Agreement (independent contractor, security, indemnity, bond terms), AUP, privacy policy, takedown and grievance procedure, refund/session-failure policy, and written opinions on BYOL, TDS/GST, and gaming-regime classification.
3. Implement IT Act §79 intermediary due diligence: published rules/AUP/privacy notice; user acknowledgment; named Grievance Officer; 24-hour complaint acknowledgment; statutory-resolution timing confirmed by counsel; timestamped takedown log; expeditious response to actual knowledge.
4. Meet DPDP Act requirements as they take effect: data minimization; separate purpose-specific consent; withdrawal and deletion paths; breach-notification runbook; encrypted and wiped provider-node session data. Treat May 13, 2027 substantive compliance as a hard product deadline.
5. Keep distance from real-money gaming: hardware-rental language only; no wagering, cash tournaments, or prize pools without fresh review; counsel memo confirming the model's treatment.
6. Use a licensed payment aggregator for collections and provider payouts; never custody customer funds. Automate TDS/GST invoices and filings from the first payout.
7. Obtain cyber liability insurance before public launch and E&O/tech liability once revenue starts.

## Layer 2 — Provider framework: five mandatory gates

A provider is a verified counterparty, not an anonymous peer.

1. **Identity:** PAN and licensed-vendor Aadhaar eKYC; verified bank account by penny-drop; one legal identity and payout account per provider.
2. **Contract:** digitally signed Provider Agreement before activation. It covers genuine contractor independence, session-data security, anti-tampering, ISP/premises responsibility, enumerated indemnity, and objective bond forfeiture terms.
3. **Attestation:** signed agent and node image; hardware fingerprint registration; image hash and agent version in heartbeats. Gaming tiers additionally require TPM-backed measured boot / remote attestation. A mismatch suspends the node.
4. **Tiered trust:**

   | Tier | Capability | Requirements |
   |---|---|---|
   | T0 Compute | Sandboxed allowlisted batch workloads | KYC, contract, signed image |
   | T1 Gaming | Licensed / green-catalog gaming | T0, attestation, latency SLA, 30-day clean record |
   | T2 BYOL AAA | User-owned-account cloud PC | T1, posted bond, dedicated GPU, 90-day clean record |

5. **Bond and reputation:** T2 requires an INR 10–25k compliant deposit/holdback structure confirmed by counsel. Forfeiture applies only to enumerated contract breaches with an appeal path. Match on uptime, session success, latency consistency, and incidents; run random canary audits for wiping and image integrity.

Providers can choose availability and workload-category opt-outs, never see credentials or session content, receive weekly payouts, and receive remediation for platform-verified workload harm.

## Layer 3 — Gaming: permission-based catalog

`rights_basis` is a hard matching filter. Only these values may schedule a title:

| Value | Meaning | Evidence |
|---|---|---|
| `direct_license` | Signed streaming/distribution agreement | Agreement and rights record |
| `cafe_commercial` | Steam PC Café commercial license | Membership and receipt |
| `explicit_permission` | Publisher's written approval | Archived correspondence |
| `byol_user_owned` | User-owned license on that user's account, T2 only | Hashed SteamID and OAuth grant record |
| `blocked` | Anything else | It does not run |

Start with direct licensing from Indian/SEA indie studios. Register the Steam PC Café program only after Valve gives written confirmation that the remote-rental model qualifies. BYOL AAA is Phase 3 only: obtain anti-cheat vendor whitelist responses and publisher consent title-by-title; use QR/device-code login; hold no password; revoke tokens at session end; use encrypted ephemeral volumes, dedicated physical GPU, stable identifiers, and verified wipes. Titles with hostile kernel anti-cheat or explicit cloud bans remain blocked.

**Permanent red lines:** no SSFN injection, hardware-ID spoofing, shared/burner accounts, Family-Sharing arbitrage, P2P game-binary distribution, credential storage/replay, nested VMs or oversubscribed gaming GPUs, DRM circumvention, or anti-cheat circumvention.

## Layer 4 — Compute: the safe revenue engine

Compute funds the business while gaming permissions are earned. v1 accepts only curated images: Blender/rendering, ML fine-tuning, media transcode, and scientific batch. Customers submit data and parameters, not arbitrary container images.

Launch requirements:

- gVisor, Firecracker, or Kata isolation; no privileged containers or host mounts; GPU only to the assigned sandbox.
- Runtime CPU/RAM/VRAM/disk caps and wall-clock timeouts.
- Default-deny egress with declared endpoint allowlists; block SMTP, IP scanning, and known C2 patterns.
- Encrypt payloads so provider host accounts cannot read inputs/outputs; destroy ephemeral scratch on completion.
- Payment-verified job submitters; business KYC above a counsel-defined spend threshold; sanctions/customer-country screening proportional to actual obligations; suspend-investigate-log abuse reports.
- Mining is banned in v1.

Arbitrary images are a later feature gated on image scanning, payment verification, account risk scoring, and production-proven egress controls.

## Layer 5 — Platform security launch gates

Before public exposure, implement AuthN/AuthZ across users, providers, and admins; mTLS and per-node certificates for agent-to-orchestrator traffic; PostgreSQL persistence; append-only audit records for sessions, jobs, takedowns, tier changes, and payouts; signed agent/image releases; tested incident response; backup restoration; and responsible disclosure.

## Revenue guardrails

| Stream | Basis | When |
|---|---|---|
| Curated compute | Customer ToS + Provider Agreement | Months 2–3 |
| Indie gaming | `direct_license` | Months 3–4 |
| Café titles | `cafe_commercial` | After Valve confirmation |
| BYOL cloud-PC rental | `byol_user_owned`, T2 | Phase 3 only |
| Indie cloud QA/test farms | Direct B2B agreement | Month 4+ |

BYOL invoices and marketing sell **GPU cloud-PC rental per hour**, never games. Provider payout must remain at or below 70–80% of session price to cover payment fees, tax administration, insurance, support, and margin. Track gross margin per GPU-hour, session success, provider churn, and two-sided CAC from week one.

## Phase gates

| Phase | Window | Entry / exit gate |
|---|---|---|
| 0 Foundation | Weeks 0–6 | Incorporation, counsel, policies, CA/GST, payment aggregator, grievance officer, insurance quotes. Exit: all Layer 1 controls complete. |
| 1 Compute revenue | Months 2–4 | Entry: Phase 0 complete and external sandbox review. Exit: 25+ verified providers, 10+ paying customers, zero unresolved abuse incidents, proven takedown drill. |
| 2 Green-zone gaming | Months 4–7 | Entry: signed licenses, working attestation, hard `rights_basis` filter. Exit: 500+ real sessions, ≥95% success, zero rights complaints. |
| 3 Permissioned BYOL AAA | Months 7–12 | Entry: anti-cheat written response, counsel sign-off, live T2 bond structure. Exit: 60 days with no platform-attributable account action. |
| 4 Scale | Month 12+ | Automated gated provider onboarding, fresh counsel for each new jurisdiction, enterprise compute, evidence pack for fundraising. |

## Evidence pack and standing rules

Keep an indexed, access-controlled repository plus counsel copy of incorporation and IP records, every license/provider agreement, Valve/publisher/anti-cheat correspondence, KYC and tax records, grievance/takedown log, quarterly audit-log exports, counsel opinions, insurance policies, and founder decisions rejecting red-line shortcuts. A regulator, publisher, or court must be answerable from this evidence within 24 hours.

1. **No document → no deployment.**
2. **Opt-in, never opt-out** for third-party content or platforms.
3. **Never touch credentials, game files, or DRM.**
4. **Every provider is verified**, not a peer.
5. **Compute funds the company; gaming builds the moat.**
6. **When in doubt, block/suspend/pause and ask counsel.**
