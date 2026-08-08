/**
 * Canonical startup knowledge base.
 *
 * Single source of truth served to every AI tool via GraphQL/MCP.
 * Distilled from docs/PLAN.md, SAFE-EXECUTION-PLAN.md, RISK-REGISTER.md,
 * docs/ROLES.md, docs/COMPETITOR-ANALYSIS.md, business_plan_review.md.
 * Keep this in sync when those docs change (consider a CX task agent).
 */

export const COMPANY = {
  name: 'Decentralized-Network',
  tagline: 'P2P Compute & Cloud Gaming Marketplace (India-first)',
  mission:
    'A two-sided marketplace routing compute workloads and cloud-gaming sessions to ' +
    'verified, contracted, attested, bonded provider nodes across India. ' +
    'Permission-based operation: nothing runs on the platform without a permitting document.',
  repository: 'https://github.com/RUSHAB3979/Decentralized-Network',
  hq: 'India',
  founded: '2026',
  stage: 'Pre-seed (Phase 0 complete)',
};

export const TRACKS = [
  {
    id: 'compute',
    name: 'Compute Track',
    status: 'phase-1',
    description:
      'Sandboxed batch workloads (Blender render, ML fine-tuning, transcode, scientific) on ' +
      'curated signed images. No platform-permission dependency. Revenue engine from Day 1.',
    wedge: 'Outcome UX: paste a file -> pay with a card -> get a result. No Docker/SSH.',
  },
  {
    id: 'gaming',
    name: 'Gaming Track',
    status: 'phase-2-3',
    description:
      'Low-latency cloud gaming on a permission-gated catalog. rights_basis hard-enforced in ' +
      'matching.ts. BYOL AAA only on Tier-2 bonded nodes, gated on publisher/anti-cheat consent.',
    wedge: 'Latency + verified-provider trust, not GPU price.',
  },
];

export const PHASES = [
  {
    id: '0', name: 'Phase 0 - Foundation / Validation', status: 'complete', window: 'Weeks 0-6',
    goals: 'Corporate foundation, counsel package, CA onboarded, 25+ demand interviews, waitlist gate.',
    exitGate: 'Entity formed; 100+ waitlist or 10+ prepaid deposits; legal docs drafted.',
  },
  {
    id: '1', name: 'Phase 1 - Compute Revenue', status: 'in-progress', window: 'Months 2-4',
    goals: 'gVisor sandbox + curated images live; providers through 5 gates at T0; auth + persistence + audit log.',
    exitGate: '25+ verified providers, 10+ paying customers, zero unresolved abuse, takedown drill passed.',
  },
  {
    id: '2', name: 'Phase 2 - Green-Zone Gaming', status: 'planned', window: 'Months 4-7',
    goals: 'T1 attestation nodes; 10+ direct_license indie titles; WebRTC streaming path; reputation v1.',
    exitGate: '500+ real gaming sessions, >=95% session success, zero rights complaints.',
  },
  {
    id: '3', name: 'Phase 3 - Permissioned BYOL AAA', status: 'planned', window: 'Months 7-12',
    goals: 'T2 bonded providers; anti-cheat whitelisting; opt-in publisher titles; wipe-verification audits.',
    exitGate: 'BYOL running 60 days with zero platform-attributable account actions.',
  },
  {
    id: '4', name: 'Phase 4 - Scale', status: 'planned', window: 'Month 12+',
    goals: 'Self-serve provider onboarding; SEA expansion (fresh counsel per jurisdiction); enterprise compute; Series A.',
    exitGate: 'Sustainable unit economics; auditable evidence pack.',
  },
];

export const STANDING_RULES = [
  { id: 1, rule: 'No document -> no deployment. Titles, workloads, providers - all of them.' },
  { id: 2, rule: "Opt-in, never opt-out, for any third party's content or platform." },
  { id: 3, rule: 'The platform never touches credentials, game files, or DRM. Ever.' },
  { id: 4, rule: 'Every provider is a verified counterparty, not a peer.' },
  { id: 5, rule: 'Compute funds the company; gaming builds the moat.' },
  { id: 6, rule: 'When in doubt, block the title / suspend the node / pause the feature and ask counsel.' },
];

export const STACK_SUMMARY = {
  monorepo: 'npm workspaces (services/*, packages/*',
  language: 'TypeScript (strict, ESM)', packageManager: 'npm', runtime: 'Node 20+',
  web: 'React 18 + Vite 6 + Tailwind 3', validation: 'Zod shared contracts',
  infra: 'Docker Compose + Postgres 16 (Phase 1 persistence)',
  sandbox: 'gVisor (runsc) target; Firecracker evaluated for CPU tiers',
};

export const MODEL_ASSIGNMENTS = {
  main: 'Claude Sonnet 5', scout: 'Claude Haiku 4.5',
  librarian: 'GPT-5.6 Sol (web)', designer: 'Claude Sonnet 5',
  task: 'Claude Sonnet 5', reviewer: 'Claude Opus 5',
  'security-reviewer': 'Claude Opus 5', sonic: 'GPT-5.5 Instant',
};

/* ---- Risk Register (abbreviated; full text via `riskRegister` query/CL) ---- */
export const RISKS: Array<Record<string, unknown>> = [
  { id: 'L-01', severity: 'critical', area: 'legal', threat: 'Secondary copyright infringement', control: 'rights_basis hard filter in matching.ts; four permitted bases; Evidence Pack' },
  { id: 'L-02', severity: 'critical', area: 'legal', threat: 'Platform ToS breach / Valve shutdown', control: 'Steam PC Cafe membership; opt-in publisher consent; compute-track payroll diversification' },
  { id: 'L-03', severity: 'critical', area: 'legal', threat: 'Anti-circumvention (CA 65A / DMCA 1201)', control: 'Red-line list; clean images; no ID spoofing; signed images' },
  { id: 'L-04', severity: 'critical', area: 'legal', threat: 'Intermediary liability for user workloads', control: 'IT Act 79 safe harbor; AUP; grievance officer; takedown log' },
  { id: 'L-05', severity: 'high', area: 'legal', threat: 'DPDP Act non-compliance', control: 'Data minimization; deletion-on-request; breach runbook; DPO owner' },
  { id: 'L-08', severity: 'high', area: 'legal', threat: 'RBI payment-regulation breach', control: 'Licensed aggregator; no custody of funds' },
  { id: 'L-09', severity: 'medium', area: 'legal', threat: 'GST / TDS (194-O) on payouts', control: 'CA retained; automated deduction + filing from payout #1' },
  { id: 'T-01', severity: 'critical', area: 'technical', threat: 'Data theft from provider nodes', control: 'Encrypted ephemeral volumes; wipe-on-exit verified by canary audits' },
  { id: 'T-02', severity: 'high', area: 'technical', threat: 'Provider snooping on live sessions', control: 'Attested boot; tier gating; bond forfeiture; canary sessions; honest disclosure' },
  { id: 'T-03', severity: 'critical', area: 'technical', threat: 'Credential / OAuth-token theft', control: 'QR/device-code login only; short-lived tokens; revoke at session end; zero at-rest auth storage' },
  { id: 'T-04', severity: 'critical', area: 'technical', threat: 'Malicious workload escapes sandbox', control: 'gVisor/Firecracker isolation; curated signed images; pen-test before phase 1 exit' },
  { id: 'T-05', severity: 'high', area: 'technical', threat: 'Tampered provider agent / forged telemetry', control: 'Signed agent binaries; TPM attestation; orchestrator cross-checks' },
  { id: 'T-06', severity: 'high', area: 'technical', threat: 'MITM on streams / control plane', control: 'WebRTC DTLS-SRTP; mTLS per-node client certs; no plaintext fallback' },
  { id: 'T-07', severity: 'critical', area: 'technical', threat: 'Orchestrator compromise (crown jewels)', control: 'AuthN/AuthZ on every endpoint; vault secrets; least privilege; audit log' },
  { id: 'F-01', severity: 'medium', area: 'fraud', threat: 'Chargeback fraud spiral', control: 'Aggregator fraud tooling; velocity caps; session evidence for representment' },
  { id: 'O-01', severity: 'high', area: 'operational', threat: 'Provider supply collapse (cold-start)', control: 'Weekly payouts; LAN-cafe / mining-rig channel; compute demand as utilization floor' },
];

/* ---- Engineering roles (abbreviated; see docs/ROLES.md) ---- */
export const ROLES: Array<Record<string, string>> = [
  { id: 'R1', title: 'Distributed Systems Architect', squad: 'engineering', focuses: 'matching.ts, scheduler, trust tiers, heartbeat protocol' },
  { id: 'R2', title: 'Network & Streaming Engineer', squad: 'engineering', focuses: 'WebRTC, STUN/TURN, DTLS-SRTP, NVENC, latency probes' },
  { id: 'R3', title: 'Cloud/Platform Engineer', squad: 'engineering', focuses: 'Docker/K8s, CI/CD, signed releases, secrets' },
  { id: 'R4', title: 'Security & Sandbox Engineer', squad: 'engineering', focuses: 'gVisor, egress deny-by-default, attestation, wipe verification' },
  { id: 'R5', title: 'Backend Engineer (Orchestrator)', squad: 'engineering', focuses: 'persistence, auth, audit log, job lifecycle' },
  { id: 'R6', title: 'Backend Engineer (Provider Agent)', squad: 'engineering', focuses: 'NVML, thermal kill-switch, mTLS identity, teardown' },
  { id: 'R7', title: 'Backend Engineer (Payments & Billing)', squad: 'engineering', focuses: 'Razorpay, 194-O TDS, refunds, fraud' },
  { id: 'R8', title: 'Frontend Engineer', squad: 'engineering', focuses: 'web-client UX, provider dashboard, catalog' },
  { id: 'R11', title: 'Technology/Media Lawyer', squad: 'legal', focuses: 'ToS, Provider Agreement, AUP, BYOL memo, licensing templates' },
  { id: 'R12', title: 'Privacy Officer / DPO', squad: 'legal', focuses: 'DPDP compliance, consent, breach runbook' },
  { id: 'R13', title: 'Compliance & Grievance Officer', squad: 'legal', focuses: 'IT Act 79 takedown log, complaint pipeline' },
  { id: 'R16', title: 'Indie Game BD', squad: 'growth', focuses: 'direct_license pipeline, publisher outreach' },
  { id: 'R17', title: 'Provider Supply Manager', squad: 'growth', focuses: 'recruiting, payouts, provider retention' },
  { id: 'R18', title: 'Growth / Community Manager', squad: 'growth', focuses: 'niche communities, waitlist, creator content' },
];
