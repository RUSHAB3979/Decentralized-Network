# Task List — @Shubh-tech-grow

**Roles:** R2 Networking & Streaming + R6 Provider Agent
**Owns:** `agent/`, `docs/solution/SESSION-FLOW.md`, streaming / TURN, telemetry
**Related:** [TEAM-EXECUTION-PLAN.md](TEAM-EXECUTION-PLAN.md) · [ROLES.md](ROLES.md) · [Tasks/tasks.md](Tasks/tasks.md)

Status values: `pending` · `in_progress` · `blocked` · `done`

---

## Current priority

**S1 — the NVML telemetry spike.** It needs a GPU box and nothing else, so it
is the one piece of real work on this list that no other person or milestone
can block.

---

## `agent/` is yours now

Block D closed on 2026-08-10. `agent/` has tracked files in it, which means it
has transferred to you along with the design decisions already baked in. Read
`agent/main.py` before you touch it — it is 20 lines and every one of them is
load-bearing.

Three constraints that came out of building it. They are not style preferences.

**1. The dependency list is a security boundary.**

`agent/requirements.txt` is `httpx` and `python-dotenv`. That is the whole
list, and it is short on purpose: the agent installs on a **provider's own
machine**, which is hardware we do not control. Anything listed there is
software we shipped onto a stranger's PC.

No database driver, ever. If `psycopg` appears in that file, the design has
gone wrong somewhere upstream of the file. The agent talks to the orchestrator
over HTTP and nothing else.

**2. Every network call gets an explicit timeout.**

Without one, calls do not fail — they **hang**. Docker's port proxy keeps
accepting TCP after a container stops and then never answers, so a client waits
indefinitely and the `except` block is unreachable. A hang is worse than an
error: it produces no log line, no exit code, and no signal that anything is
wrong.

And size the timeout against the server's *worst* case, not its typical one.
The agent's original 5s timeout sat in front of a `/health` that takes ~10s
when the database is down — so the `503` branch looked correct and had never
once executed. `connect_timeout` applies **per resolved address**, and
`localhost` resolves to both `::1` and `127.0.0.1`.

**3. The three-outcome contract must survive whatever you build next.**

| What happened | What it means | Exit |
|---|---|---|
| `200` | Everything works | `0` |
| Response, status `503` | Orchestrator up, **its database is down** | `1` |
| `httpx.RequestError` | Orchestrator unreachable | `1` |

The middle row is the one that gets lost. `503` and "connection refused" are
different diagnoses — alive-but-broken versus not-running-at-all — and merging
them into "error" throws away the half that tells you where to look. The exit
code matters because a scheduler reads it and a human does not.

---

## S0 — Track 0: first PR · `pending`

The plan's original Track 0 for you was "run the provider agent against the
frozen TS orchestrator." **That is superseded** — there is now a real Python
agent and a real Python orchestrator, and running those teaches you the
heartbeat path better than the frozen version ever would.

1. Add yourself a line in `CONTRIBUTORS.md` (the file does not exist yet —
   creating it is the task).
2. Run the whole stack from the README's Windows quick start: Postgres →
   orchestrator → agent.
3. Run the **failure** cases too. Stop Postgres, run the agent, confirm `503`
   and exit `1`. Stop uvicorn, run it again, confirm `WinError 10061` and exit
   `1`.

Step 3 is the actual assignment. You are about to extend this agent into a
loop, and you need to have *seen* each failure before you write code that
handles it.

- [ ] `CONTRIBUTORS.md` line, PR merged
- [ ] Full stack running locally
- [ ] Both failure modes observed first-hand

---

## S1 — NVML telemetry spike · `pending` · **start here**

A standalone script that reads real GPU stats from a real GPU.

**It lives in `docs/spikes/`, not `agent/`.** A spike is an experiment whose
job is to answer a question; the moment it lands in `agent/` it becomes
something people depend on before anyone decided it should exist.

Answer these, in writing:

- [ ] Which library, and what it requires on the provider's machine (driver
      version, package, admin rights?)
- [ ] Which metrics are readable: utilisation, VRAM used/total, temperature,
      power draw, fan, encoder sessions
- [ ] **Which are readable without admin privileges** — this decides whether
      the agent can run as a normal user, which decides how many providers will
      actually install it
- [ ] Cost per sample: how long does a read take, can it run every few seconds
      without measurably affecting a game
- [ ] What happens with **no NVIDIA GPU**, an AMD GPU, or a laptop with hybrid
      graphics. Most people's machines are not your machine
- [ ] What happens when the GPU is fully loaded — does the read block?

Deliver `docs/spikes/nvml-telemetry.md` plus the script. The document matters
more than the script: the script proves it works on your box, the document is
what survives.

---

## S2 — Transport decision · `pending`

A written decision on how session media actually moves: WebRTC versus the
alternatives.

- [ ] Options considered, and why each was kept or dropped
- [ ] **TURN cost estimate with the arithmetic shown.** Relayed sessions are
      the expensive case — bandwidth per session × expected relay fraction ×
      hours. A guess with the working shown can be corrected later; a bare
      number cannot
- [ ] What fraction of connections realistically need TURN rather than direct
      P2P, and what that assumption rests on
- [ ] Latency budget, end to end, with a number against each hop
- [ ] Codec and encoder assumptions, and what they require of a provider's GPU

Deliver as `docs/spikes/transport-decision.md`. This is the input to R2 work
in later milestones, and it constrains hardware requirements — so being wrong
here is expensive later, and being *undecided* here blocks streaming entirely.

---

## S3 — Agent heartbeat loop · `blocked` (needs M1)

Waits on R1's Pydantic models — those ship first and everything else in M1
depends on their shape. Do not start against a guessed contract.

When it unblocks:

- [ ] Loop every N seconds, N from config, not hardcoded
- [ ] Sends capability + metrics per the shipped models
- [ ] **Survives the orchestrator being down.** A heartbeat loop that exits on
      the first failed request is useless — the orchestrator restarting must
      not require every provider to restart their agent
- [ ] Backs off on repeated failure rather than hammering a struggling server
- [ ] Still distinguishes the three outcomes above
- [ ] Logs enough to diagnose a provider's problem remotely, and no secrets

---

## S4 — `SESSION-FLOW.md` · `ongoing`

You own `docs/solution/SESSION-FLOW.md`. Keep it true as the transport and
telemetry decisions land. A flow document that describes an intention rather
than the system is worse than no document, because people trust it.

---

## Notes

Add a dated line when something changes.

| Date | Note |
|------|------|
| 2026-08-10 | File created. `agent/` transferred on Block D completion. S0 supersedes the plan's "run the frozen TS agent" — a real Python agent now exists. |
