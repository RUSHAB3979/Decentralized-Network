# AI Smart Usage Plan — P2P Compute Marketplace

**Date:** August 8, 2026
**Scope:** Optimal AI model assignment across Oh My Pi (OMP) harness roles for maximum development velocity
**Subscriptions:** ChatGPT Plus ($20/mo) + Claude Pro ($20/mo) = $40/mo total

---

## 1. Startup Context

We are building a **P2P Compute & Cloud Gaming Marketplace** (India-first) — a decentralized platform that routes workloads to verified provider machines across two tracks:

- **Compute Track (Phase 1):** Sandboxed batch workloads (Blender rendering, ML fine-tuning, media transcode) on curated signed images. Zero third-party permission dependency. Revenue engine from Day 1.
- **Gaming Track (Phase 2–3):** Low-latency cloud gaming sessions with permission-based catalog (`rights_basis` hard filter in `matching.ts`). Gated behind signed licenses, Valve PC Cafe Program confirmation, and anti-cheat whitelisting.

### Tech Stack
- **Orchestrator:** Node.js / TypeScript / FastAPI control plane
- **Provider Agent:** TypeScript daemon with NVML monitoring + heartbeat
- **Contracts:** Shared Zod schemas (`packages/contracts`)
- **Frontend:** React + Vite + Tailwind CSS (`web-client/`)
- **Infrastructure:** Docker Compose, PostgreSQL (planned), gVisor/Firecracker (sandbox roadmap)
- **Repository:** [github.com/RUSHAB3979/Decentralized-Network](https://github.com/RUSHAB3979/Decentralized-Network)

### Current Phase
Phase 0 complete (baseline MVP). Working toward Phase 1 (Persistence + Reliability) and Phase 2 (Scheduling + Execution Control).

### Key Documents
| Document | Purpose |
|---|---|
| `docs/PLAN.md` | Product + engineering milestones |
| `docs/ARCHITECTURE.md` | System architecture and component boundaries |
| `SAFE-EXECUTION-PLAN.md` | Legal, platform, provider, and revenue blueprint |
| `RISK-REGISTER.md` | Complete threat map with technical/legal/process controls |
| `docs/COMPETITOR-ANALYSIS.md` | Market positioning vs Vast.ai, io.net, Akash, Salad |
| `docs/AAA-RENTAL-PLAN.md` | BYOL cloud gaming technical design |

---

## 2. Available AI Models (August 2026)

### ChatGPT Plus ($20/month)

| Model | Type | Strengths |
|---|---|---|
| **GPT-5.6 Sol** | Flagship Reasoning | Repository-level awareness, agentic orchestration, adjustable reasoning depth (Medium/High/Extra-High), native web search, DALL-E image generation, Python code execution |
| **GPT-5.5 Instant** | Fast Default | Ultra-low latency for quick tasks, summaries, and lightweight background operations |
| **GPT-5.6 Terra** | Balanced | ~50% cost of Sol with comparable performance for standard tasks |
| **GPT-5.6 Luna** | Efficient | Optimized for high-volume, low-cost operations (PR triage, summaries) |

### Claude Pro ($20/month)

| Model | Type | Strengths |
|---|---|---|
| **Claude Fable 5** | Mythos-Class Frontier | 1M token context, SWE-bench Pro leader, autonomous long-horizon coding, tool generalization (strict rate limits) |
| **Claude Opus 5** | Premium Frontier | Self-verification (builds own test harnesses), pushback on faulty instructions, complex multi-file architecture, long agentic chains |
| **Claude Sonnet 5** | Balanced Workhorse | Best speed-to-intelligence ratio, adaptive thinking, default for daily coding, near-frontier reasoning at lower cost |
| **Claude Haiku 4.5** | Speed & Scale | Ultra-fast, low-latency, high-throughput tasks, code documentation, simple routing |

---

## 3. Oh My Pi Bundled Agent Roles

The OMP harness provides **7 bundled subagent roles** that can be dispatched concurrently (up to 32 parallel agents):

| Agent | Type | Responsibility |
|---|---|---|
| `scout` | **Read-Only** | Fast codebase exploration, pattern searches, dependency mapping, file tree indexing. Gets verbatim file content (no summarization). Never edits files. |
| `librarian` | **Read-Only** | Researches external libraries and APIs by reading source code and documentation. Returns source-verified answers. Gets verbatim file content. |
| `designer` | **Read-Write** | UI/UX specialist for design implementation, visual refinement, and frontend component building. |
| `task` | **Read-Write** | General-purpose worker with full capabilities for delegated multi-step tasks. Default agent when none is specified. |
| `reviewer` | **Read-Only** | Code review specialist for quality, correctness, and security analysis. |
| `security-reviewer` | **Read-Only** | Evidence-backed repository vulnerability discovery. Read-only deep security audit. |
| `sonic` | **Read-Write** | Low-reasoning agent for strictly mechanical updates, bulk renames, or data collection only. |

### OMP Model Role Aliases

| Role | Purpose |
|---|---|
| `@default` | Primary session model |
| `@smol` | Fast/cheap model for lightweight background tasks (session titles, memory, difficulty classification) |
| `@slow` | Most capable model for hardest problems |
| `@tiny` | Lightest model for background housekeeping (falls back to `@smol` when unset) |
| `@task` | Default worker model for subagents |
| `@plan` | Planning/architecture phase model |
| `@designer` | UI/UX implementation model |
| `@vision` | Image/screenshot analysis |
| `@commit` | Commit message generation |
| `@advisor` | Advisory/watchdog model |

---

## 4. Model-to-Role Assignment Matrix

### Agent Assignments

```
                          ┌────────────────────────────────┐
                          │   Main Agent (You + OMP)       │
                          │     Claude Sonnet 5 (@default) │
                          └───────────────┬────────────────┘
                                          │
    ┌──────────────┬──────────────┬───────┴──────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼              ▼              ▼
┌────────┐    ┌─────────┐    ┌──────────┐   ┌─────────┐    ┌──────────┐   ┌─────────┐
│ scout  │    │librarian│    │ designer │   │  task   │    │ reviewer │   │  sonic  │
│Haiku4.5│    │GPT-5.6  │    │Sonnet 5  │   │Sonnet 5 │    │ Opus 5   │   │GPT-5.5  │
│        │    │Sol(Web) │    │          │   │         │    │          │   │Instant  │
└────────┘    └─────────┘    └──────────┘   └─────────┘    └──────────┘   └─────────┘
```

| OMP Agent | Assigned Model | Reasoning |
|---|---|---|
| **`scout`** | **Claude Haiku 4.5** | Read-only exploration needs raw speed, not deep reasoning. Preserves Sonnet/Opus rate limits for editing. 200k context ingests large file trees efficiently. |
| **`librarian`** | **GPT-5.6 Sol** | Must verify external API docs (Razorpay, Steam API, gVisor docs). GPT-5.6 Sol has **native web search** — Claude models cannot browse the internet. Critical for researching payment aggregator APIs, DPDP Act compliance requirements, and sandbox runtime docs. |
| **`designer`** | **Claude Sonnet 5** | Frontend implementation (React + Tailwind in `web-client/`) benefits from Claude's Artifacts workspace for live component preview. Adaptive thinking handles CSS layout and responsive design efficiently. |
| **`task`** | **Claude Sonnet 5** | Default workhorse for multi-step feature implementation across `services/orchestrator/`, `services/provider-agent/`, and `packages/contracts/`. Best speed-to-intelligence ratio for production TypeScript code. |
| **`reviewer`** | **Claude Opus 5** | Code review demands self-verification. Opus 5 builds its own test harnesses to validate findings and pushes back on faulty patterns — critical for catching edge cases in `matching.ts`, job lifecycle state machines, and provider trust controls. |
| **`security-reviewer`** | **Claude Opus 5** | Deep chain-of-thought required to trace auth flows, race conditions, and injection vectors across the orchestrator. Maps directly to Risk Register threats T-03 (credential theft), T-04 (sandbox escape), and T-07 (orchestrator compromise). |
| **`sonic`** | **GPT-5.5 Instant** | Mechanical bulk updates (mass import rewrites, boilerplate Zod schema generation, file renames) need zero reasoning depth. Cheapest and fastest option. |

### Role Alias Assignments

| OMP Role | Assigned Model | Reasoning |
|---|---|---|
| `@default` | **Claude Sonnet 5** | Primary pair-programming model. Best balance of speed, coding quality, and natural language for daily orchestrator/agent development. |
| `@smol` | **Claude Haiku 4.5** | Background tasks (session titles, memory indexing, auto-thinking classification). Ultra-fast, preserves heavy-model rate limits. |
| `@slow` | **Claude Opus 5** | Reserved for the hardest problems: complex state machine debugging in job lifecycle, multi-file refactors across orchestrator + agent + contracts. |
| `@tiny` | **GPT-5.5 Instant** | Lightest housekeeping tasks. Near-zero latency for commit titles and quick classifications. |
| `@task` | **Claude Sonnet 5** | Worker subagents inherit this model. Ensures consistent high-quality code generation across parallel task batches. |
| `@plan` | **GPT-5.6 Sol:high** | Architecture planning (Phase 1-4 milestone design, sandbox runtime selection, database schema planning) benefits from Sol's repository-level awareness and adjustable reasoning depth. |
| `@designer` | **Claude Sonnet 5** | UI/UX implementation with Artifacts live preview for `web-client/` React components. |
| `@vision` | **GPT-5.6 Sol** | Screenshot and image analysis (UI mockup review, architecture diagram interpretation). |
| `@commit` | **Claude Haiku 4.5** | Commit message generation. Fast, concise, no reasoning overhead needed. |
| `@advisor` | **GPT-5.6 Sol:medium** | Watchdog/advisory model for monitoring session quality and flagging potential issues. |

---

## 5. OMP Configuration

### `~/.omp/agent/config.yml`

```yaml
# =============================================================
# AI Smart Usage — Model Role Configuration
# P2P Compute Marketplace (Decentralized-Network)
# =============================================================

modelRoles:
  default: "anthropic/claude-sonnet-5"
  smol: "anthropic/claude-haiku-4-5"
  slow: "anthropic/claude-opus-5"
  tiny: "openai/gpt-5.5-instant"
  task: "anthropic/claude-sonnet-5"
  plan: "openai/gpt-5.6-sol:high"
  designer: "anthropic/claude-sonnet-5"
  vision: "openai/gpt-5.6-sol"
  commit: "anthropic/claude-haiku-4-5"
  advisor: "openai/gpt-5.6-sol:medium"

# Per-agent model overrides for subagent dispatch
task:
  agentModelOverrides:
    scout: "anthropic/claude-haiku-4-5"
    librarian: "openai/gpt-5.6-sol"
    designer: "anthropic/claude-sonnet-5"
    task: "anthropic/claude-sonnet-5"
    reviewer: "anthropic/claude-opus-5"
    security-reviewer: "anthropic/claude-opus-5"
    sonic: "openai/gpt-5.5-instant"
```

---

## 6. Workflow Execution Patterns

### Pattern A: Feature Implementation (Parallel Workers)
```
Main (Sonnet 5) decomposes task
  ├── scout (Haiku 4.5)     → Maps affected files in services/orchestrator/
  ├── librarian (Sol + Web) → Verifies external API signatures
  └── task ×3 (Sonnet 5)    → Parallel implementation across orchestrator, agent, contracts
      └── reviewer (Opus 5) → Final quality gate before merge
```

### Pattern B: Security Audit (Deep Analysis)
```
Main (Sonnet 5) scopes audit against RISK-REGISTER.md
  ├── scout (Haiku 4.5)          → Indexes all auth/crypto/session code paths
  └── security-reviewer (Opus 5) → Deep vulnerability scan mapped to T-01 through T-14
```

### Pattern C: UI Sprint (Designer + Worker)
```
Main (Sonnet 5) defines component requirements
  ├── designer (Sonnet 5)   → Builds React components with Artifacts preview
  └── task (Sonnet 5)       → Wires API integration and state management
```

### Pattern D: Bulk Refactor (Mechanical)
```
Main (Sonnet 5) defines the codemod
  └── sonic ×N (Instant)    → Mass import rewrites, Zod schema updates, file renames
```

---

## 7. Rate Limit Management

### Claude Pro Limits
- ~45 messages per 5 hours (varies by prompt size)
- Large context uploads (100k+ tokens) reduce the message count per window

### ChatGPT Plus Limits
- GPT-5.6 Sol: ~80 messages per 3 hours (dynamic)
- GPT-5.5 Instant: High limits (rarely hit)

### Conservation Strategy
1. **Never use Opus 5 or Fable 5 for scouting** — use Haiku 4.5 for all read-only exploration.
2. **Batch subagent tasks** — dispatch up to 32 concurrent agents in a single `tasks[]` array to minimize round trips.
3. **Pass large payloads via file paths** (`local://<path>`) instead of pasting code inline.
4. **Reserve Opus 5 for review/security gates only** — it has the strictest rate limits.
5. **Use GPT-5.5 Instant for all mechanical work** — keeps Claude rate limits available for intelligent tasks.

---

## 8. Startup-Specific Model Usage Rules

| Startup Task | Model | Why |
|---|---|---|
| Writing `matching.ts` rights_basis filter | Sonnet 5 | Core business logic needs reliable, clean TypeScript |
| Reviewing provider 5-gate onboarding code | Opus 5 | Security-critical; self-verification catches auth flaws |
| Researching DPDP Act 2023 compliance | Sol (Web) | Needs live web search for latest Indian regulatory updates |
| Building CatalogView / SessionView UI | Sonnet 5 | Artifacts preview for React + Tailwind components |
| Designing gVisor sandbox integration | Sol:high | Architecture planning needs deep reasoning + web research |
| Bulk-updating Zod schemas in contracts/ | Instant / Haiku | Mechanical transformation, zero reasoning needed |
| Writing Provider Agreement legal templates | Sonnet 5 | Natural, human-like writing without AI cliches |
| Auditing orchestrator for T-07 threats | Opus 5 | Deep security review of control plane endpoints |
| Generating commit messages | Haiku 4.5 | Fast, concise, no overhead |
| Indie publisher outreach emails | Sonnet 5 | Professional tone, no robotic language |

---

## 9. Standing Rules

1. **Scout before you edit.** Always dispatch `scout` (Haiku 4.5) to map affected files before spawning `task` workers.
2. **Web research goes through `librarian` (Sol).** Claude cannot browse the internet. Any external API or legal research must use GPT-5.6 Sol.
3. **Security gates use Opus 5.** Every PR touching auth, payments, credentials, or provider trust must pass through `reviewer` or `security-reviewer` on Opus 5.
4. **Mechanical work uses `sonic`.** Never waste Sonnet/Opus rate limits on import rewrites, file renames, or boilerplate.
5. **Skip formatters and linters in subagents.** Run those once at the end, not inside each parallel worker.

---

*This plan is a living document. Review quarterly alongside the Risk Register and Safe Execution Plan. Update model assignments when new model generations ship or rate limits change.*
