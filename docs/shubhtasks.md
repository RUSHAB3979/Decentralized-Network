# Task List — @Shubh-tech-grow

**Roles:** R2 Networking & Streaming + R6 Provider Agent
**Owns:** `agent/`, `docs/solution/SESSION-FLOW.md`, streaming / TURN, telemetry
**Co-owns (from 2026-08-12):** `docker-compose.yml` and the build jobs in
`.github/workflows/ci.yml`, alongside [@YogitaKanwar](https://github.com/YogitaKanwar)
**Related:** [TEAM-EXECUTION-PLAN.md](TEAM-EXECUTION-PLAN.md) · [ROLES.md](ROLES.md) · [Tasks/tasks.md](Tasks/tasks.md)

Status values: `pending` · `in_progress` · `blocked` · `done`

---

## Current priority

**S3a — the 503 bug in `agent/reporter.py`.** Half an hour, and it is a defect
in code that already shipped. Do it first so the next PR starts from a clean
file. Then **S5 — inference ingress**, which is the largest unowned piece of
networking in the repo and is on M2's critical path.

**S1** stays available whenever you have the GPU box and no orchestrator: it
needs neither.

### A note on what changed under you

[ADR 0003](adr/0003-inference-beachhead.md) (Accepted 2026-08-11) moved the
beachhead market from cloud gaming to LLM inference. Read it before S5.

It did not remove your role — it changed which network problem the role is
pointed at. WebRTC, ICE, TURN and the 16 ms frame budget leave the critical
path. What replaces them is not smaller: a customer's inference request still
has to reach Ollama on a stranger's home PC that has no public address, no port
forward, and quite possibly carrier-grade NAT in front of it. That is the same
NAT-traversal problem wearing different clothes, and nobody owns it yet.

S2 and S4 are left standing as written. The transport decision and
`SESSION-FLOW.md` describe the deferred gaming path, so treat them as *not
current* rather than as instructions — ADR 0003 says gaming is deferred, not
abandoned, and that work becomes live again the day it resumes.

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

## S1 — NVML telemetry spike · `pending`

A standalone script that reads real GPU stats from a real GPU.

**Scope changed since this was written.** `agent/telemetry.py::detect_gpu()`
already reads name, VRAM total/used, utilisation, temperature and driver
version by shelling out to `nvidia-smi --query-gpu`, in
shipped code. So there is an incumbent, and the spike is now a comparison
rather than a greenfield choice: does NVML beat parsing `nvidia-smi` output on
cost per sample, on failure behaviour, and on what it needs installed? Answer
that and the questions below still stand.

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

## S3 — Agent heartbeat loop · `done` (built during M1, 2026-08-11)

This was blocked on R1's Pydantic models. M1 was then built in one pass rather
than by the per-person split, so the loop already exists as `agent/reporter.py`
and `agent/identity.py`. **The split still stands for review ownership** — the
file is on your surface, you own it now, and the six criteria below were the
acceptance test it was written against.

| # | Criterion | Met |
|---|---|---|
| 1 | Loop every N seconds, N from config, not hardcoded | ✅ `DEFAULT_INTERVAL_S`, overridden by the server's `heartbeat_interval_s` |
| 2 | Sends capability + metrics per the shipped models | ✅ `capability_payload()` / `metrics_payload()` |
| 3 | Survives the orchestrator being down | ✅ the loop never returns except on `stop` |
| 4 | Backs off on repeated failure | ✅ doubling to `MAX_BACKOFF_S` = 120s, resets on success |
| 5 | Still distinguishes the three outcomes | ❌ **see S3a** |
| 6 | Logs enough to diagnose remotely, no secrets | ✅ |

Read the module docstring before changing anything. Three decisions in it are
load-bearing: the loop never gives up, a `404` means *re-register* rather than
*fail*, and the client timeout (15s) is deliberately larger than the
orchestrator's own database connect timeout (5s) so that healthy-but-slow is
never reported as an error.

---

## S3a — the 503 is being logged as unreachable · `pending` · **do this first**

Your own criterion 5 is not met, and the failure is exactly the one your
three-outcome table warns about.

`agent/reporter.py:200` catches `httpx.HTTPError`. `HTTPStatusError` — what
`raise_for_status()` throws on a `503` — is a subclass of it, so an orchestrator
that is alive but has lost its database lands in the same branch as a refused
connection and prints:

```
[reporter] cannot reach http://localhost:8080: HTTPStatusError: ...
```

The orchestrator *was* reached. "Cannot reach" sends whoever reads that log to
the wrong half of the system.

- [ ] Catch `httpx.HTTPStatusError` ahead of the general handler and log the
      status code and the fact that a response arrived
- [ ] Keep the retry behaviour identical — a `503` is still retryable, this is
      a diagnosis change, not a control-flow change
- [ ] A test in `agent/tests/test_reporter.py` that asserts the two cases
      produce different log lines. Without it this regresses the first time
      somebody simplifies the handler

---

## S4 — `SESSION-FLOW.md` · `ongoing`

You own `docs/solution/SESSION-FLOW.md`. Keep it true as the transport and
telemetry decisions land. A flow document that describes an intention rather
than the system is worse than no document, because people trust it.

---

## S5 — Inference ingress: how a request reaches a machine with no address · `pending`

**This is the R2 headline task and it replaces S2 as the live transport
question.** M2 cannot ship without an answer.

Today the agent is outbound-only. It dials the orchestrator, the orchestrator
never dials it. Ollama listens on `127.0.0.1:11434` and is not exposed. That is
correct and it must stay correct — the moment a provider has to open a port on
their router, the install rate collapses and the attack surface becomes a
stranger's home network.

So: a customer sends a prompt to our gateway. How does it get to that Ollama?

Options to weigh, with the same rigour S2 asked for:

- [ ] **Agent-initiated persistent connection.** The agent holds open a
      WebSocket (or long-poll, or SSE) to the control plane and *pulls* work.
      Nothing inbound, works behind any NAT. Cost: one held connection per
      provider on the server, forever, and the reconnect story is the whole
      design
- [ ] **Reverse tunnel** to an edge relay. Similar shape, more moving parts,
      and it puts bytes through infrastructure we pay for — this is TURN's
      cost problem again, so bring the arithmetic
- [ ] **Direct inbound (UPnP / port forward / STUN hole-punch).** Say why it is
      rejected rather than leaving it unmentioned. HTTP request/response over a
      hole-punched UDP path is not free
- [ ] **Bandwidth arithmetic, shown.** A streamed completion is small; a model
      pull is gigabytes. Which one dominates a provider's monthly cap, and what
      does that do to an Indian home broadband plan
- [ ] **Latency budget per hop**, gateway → relay → provider → first token
- [ ] **What happens to an in-flight request when the provider's link drops.**
      Half a completion is worse than none if the customer was billed for it

Two constraints that are not yours to change:

1. **A customer token never reaches a provider machine.** It terminates at the
   gateway. Whatever you design carries work, not credentials.
2. `agent/requirements.txt` is a security boundary. If the answer needs a new
   dependency on the provider's PC, that is a decision to argue for explicitly,
   not a line added in passing.

Deliver `docs/spikes/inference-ingress.md` plus a **two-machine proof** — a
request entering on one box and answered by Ollama on another that has no port
open. The document is what survives; the proof is what makes it credible.

---

## S6 — Reachability and region, measured not claimed · `pending`

The heartbeat currently accepts whatever a node says about itself. Risks T-05
(telemetry forgery) and T-14 (region fraud) both live here, and both survived
the pivot untouched: a node claiming to be in Mumbai when it is in Frankfurt
misprices every request routed to it.

- [ ] RTT measured from the control plane, recorded per heartbeat
- [ ] What a single vantage point can and cannot prove, and what a second one
      buys — with the honest answer about how cheaply it is defeated
- [ ] Where the measurement belongs: in the heartbeat response, a separate
      probe, or the ingress path from S5. They have different failure modes

Smaller than S5 and downstream of it — the ingress design decides where a probe
can even be taken from. Start it after S5's shape is settled.

---

## S7 — `docker compose up` starts the wrong stack · `pending` · DevOps

You co-own `docker-compose.yml` from today. It has a live defect.

The file still brings up the **frozen TypeScript** services: `image: node:20`
running `npm run dev:orchestrator` and `npm run dev:agent`, which resolve to
`services/orchestrator` and `services/provider-agent`. Those are read-only
reference code under clash rule 4. The stack people actually run is Python —
`orchestrator/` and `agent/` — and the README's quick start works around this
by telling everyone to type `docker compose up -d db` and start the rest by
hand.

That workaround is why the file rotted without anyone noticing: nothing in
daily use ever renders the broken half. CI only runs `docker compose config
--quiet`, which proves the YAML parses, not that the services are the right
ones.

- [ ] Compose brings up the Python orchestrator against Postgres
- [ ] Decide, in writing, whether the agent belongs in compose at all. It is a
      Windows desktop app with a tray icon and a WebView2 window; a Linux
      container cannot run it, and pretending otherwise is how the file rotted
      the first time
- [ ] `docker compose up` with no service argument does something correct, or
      fails with a message that says what to type instead
- [ ] README's quick start updated to match whatever you land

**Coordinate with @YogitaKanwar before opening the PR** — she is the other
owner of this file and R3 is her role. Co-ownership means the conversation
happens, not that it is skipped.

---

## S8 — CI never runs the agent on Windows · `pending` · DevOps

The `python` job in `.github/workflows/ci.yml` runs on `ubuntu-latest` and
installs `orchestrator/requirements.txt` only. `agent/requirements.txt` is
never installed by anything.

So the agent's tests pass in CI for a reason that is an accident:
`agent/reporter.py` deliberately imports nothing from `agent.ui`, which is what
lets it be collected on a runner with no `pystray`, `pywebview` or `pillow`
installed. That is a real design property and worth keeping — but right now it
is the *only* thing standing between us and a green build on code that cannot
start on the platform it ships to. Nothing tests the tray, the WebView2 window,
`CREATE_NO_WINDOW`, or DPAPI, and none of those exist on Linux.

- [ ] A `windows-latest` job that installs `agent/requirements.txt` and runs
      the agent's tests
- [ ] Proof that the pins in `agent/requirements.txt` resolve on a clean
      Windows machine — that install is itself the check, exactly as the
      orchestrator's is today
- [ ] Keep the Linux job. The point is not to move the tests, it is that a
      module which must import without the UI installed keeps being proven to
- [ ] Watch the runtime. Windows runners are slower and billed at a higher
      multiplier; if the job is slow, say what it costs rather than letting it
      quietly become the reason nobody runs CI

`ci.yml` is co-owned three ways — @YogitaKanwar owns the build jobs, and
@ryujikentaro owns the gitleaks/trivy/SBOM gates in the same file. Touch the
build jobs, leave the security gates alone.

---

## Notes

Add a dated line when something changes.

| Date | Note |
|------|------|
| 2026-08-10 | File created. `agent/` transferred on Block D completion. S0 supersedes the plan's "run the frozen TS agent" — a real Python agent now exists. |
| 2026-08-12 | **S3 closed as done** — it was built during M1's single-pass implementation rather than by the per-person split, and criterion 5 came out unmet, which is now S3a. **S2 and S4 left standing but no longer current**: ADR 0003 deferred cloud gaming on 2026-08-11, which takes WebRTC, ICE and TURN off the critical path. **Four tasks added.** S5 and S6 are R2 work repointed at the inference market — the NAT problem did not go away, it changed shape. S7 and S8 are DevOps, on the back of co-ownership of `docker-compose.yml` and `ci.yml`'s build jobs granted the same day. |
