# The Provider App — code reference

How every part of the live Python code works, how it does it, and why it was
built that way. Written to be read by someone who has to fix this at 2am
without the author present.

**Scope.** `agent/` (the provider app), `orchestrator/` (the control plane as it
exists today), and the desktop half of `web-client/`. The TypeScript under
`services/` and `packages/contracts/` is a frozen contract reference and is
deliberately not covered — see [ADR 0002](adr/0002-generated-vs-handbuilt.md).

**The one question this codebase is organised around.** ADR 0002 splits the
system by a single test: *if this is wrong, will something reliably raise?*
Code that throws on failure is generated. Code that degrades quietly is
hand-built. Almost every design decision documented below is downstream of that
question, and the comments in the source say so explicitly. When you change
something here, ask the question again before you decide how carefully to work.

---

## 1. What the app is

`GPUProvider.exe` is a single Python process that a provider installs on their
gaming PC. It does four things today:

1. Finds or starts **Ollama**, the LLM inference runtime.
2. Watches that Ollama stays up, and reports the node's status.
3. Shows that status in a **system tray icon** and a **native desktop window**.
4. **Registers with the orchestrator and heartbeats telemetry to it** (M1).

What it deliberately does *not* do yet: authenticate, take a lease, or meter
anything. The heartbeat carries no credential — see
[ADR 0004](adr/0004-m1-unauthenticated-heartbeat.md) for exactly what that costs
and the conditions under which it must stop. `agent/core/` is still three
unimplemented interfaces. That absence is a decision, not an omission: the app
runs and can be tested today, so the hand-built parts get written carefully
rather than under pressure to make the thing start.

The window is Edge **WebView2** rendering a React bundle loaded from disk over a
`file://` URL. There is no HTTP server and no origin. This is why the executable
is 23.6 MB rather than Electron-sized: WebView2 already ships with Windows, so
the app carries no browser engine.

```
┌─────────────────────────── GPUProvider.exe ───────────────────────────┐
│                                                                       │
│  main thread          worker thread     detached thread   reporter    │
│  ┌────────────┐      ┌────────────┐    ┌────────────┐   ┌──────────┐  │
│  │ pywebview  │      │ _supervise │    │  pystray   │   │ reporter │  │
│  │ WebView2   │      │  15s poll  │    │ tray icon  │   │ .run()   │  │
│  │ window     │      └─────┬──────┘    └─────┬──────┘   └────┬─────┘  │
│  └─────┬──────┘            │                 │               │        │
│        │   ┌───────────────┴─────────────────┴───────────────┘        │
│        └───┤        ProviderState  (lock + listeners)                 │
│            └───────────────┬──────────────────────────────┬───────────│
│                            │                              │           │
│                    OllamaSupervisor                        │          │
└────────────────────────────┼───────────────────────────────┼──────────┘
                             │ HTTP                          │ HTTP
                       127.0.0.1:11434                 ORCHESTRATOR_URL
                          Ollama                    /providers/heartbeat
```

The reporter thread only ever *reads* `ProviderState`. Nothing the orchestrator
says can change this machine's status — that would make a remote party able to
mark a provider's own GPU busy.

---

## 2. Runtime architecture

### 2.1 Threading, and why it is shaped this way

Both `pystray` and `pywebview` want the Windows main thread. `pywebview`
genuinely requires it; `pystray` does not. So pywebview gets the main thread and
the tray runs detached via `icon.run_detached()`. Ollama supervision runs on a
third daemon thread, and M1 added a fourth for orchestrator reporting.

Four threads that must never touch each other's internals. They communicate
through exactly one object: `ProviderState`.

**Why the reporter is a separate thread rather than work inside `_supervise`.**
The two loops fail independently and must be allowed to. An orchestrator outage
must not stop Ollama supervision — the provider's own tray icon would freeze on
a stale status because a server they do not run went down. The inverse matters
too: a node whose Ollama has died still has to keep heartbeating, precisely so
the marketplace learns it is unusable rather than merely silent.

### 2.2 Boot sequence — `agent/app.py:73`

```
main()
 ├─ load_dotenv()                      picks up ORCHESTRATOR_URL from source runs
 ├─ ProviderState()                    status = STARTING
 ├─ OllamaSupervisor()
 ├─ accepting = Event(); accepting.set()
 ├─ Thread(_supervise, daemon=True).start()
 ├─ Thread(reporter.run, daemon=True).start()   registers, then heartbeats
 ├─ window.build(state, on_drain_change)      window created HIDDEN
 ├─ tray.build(...) → icon.run_detached()
 └─ window.run(dashboard, on_started=show)    ◀ BLOCKS main thread
```

`load_dotenv()` runs first because the reporter reads `ORCHESTRATOR_URL` at
thread start. The packaged exe ships no `.env`, which is why
`reporter.DEFAULT_ORCHESTRATOR` is a working value rather than a required
variable — a missing config file must not produce a node that boots fine and
never enrols.

The window is created hidden and shown from `on_started`, i.e. once the GUI loop
is actually running. Showing it before that races the loop and can paint an
empty frame.

### 2.3 Shutdown — `agent/app.py:116`

Order matters and each step exists for a reason:

```python
stop.set()                       # tell both loops to exit
worker.join(timeout=5)           # let the supervisor finish its current poll
telemetry_reporter.join(timeout=5)  # let an in-flight heartbeat finish
supervisor.stop()                # stop Ollama IF we started it (see §3.3)
state.set(Status.STOPPED)        # last status the tray will render
dashboard.destroy()              # ends webview.start(), releasing the main thread
```

**The node is not deregistered on quit.** It cannot be: an unauthenticated
shutdown endpoint would let anyone take any node offline. So a provider who
quits stays "online" in the marketplace until the TTL ages them out — up to
120 seconds of a node advertising capacity it no longer has. That window closes
when `agent/core/creds.py` exists; it is listed there as design question 6.

Without that final `destroy()` the process survives the tray being quit, because
`webview.start()` is still holding the main thread. This is the single most
common way to leave an orphaned `GPUProvider.exe` running.

---

## 3. Module reference

### 3.1 `agent/state.py` — the shared truth

**What.** One mutable object holding `Status` (an enum) and `detail` (a
human-readable reason), with change notification.

**How.** A `threading.Lock` guards both fields. `set()` (`state.py:61`) is a
no-op when nothing changed — writing the same status repeatedly would churn the
tray icon on every 15-second poll. Listeners are collected inside the lock and
then **fired outside it** (`state.py:70`), so a listener that redraws the tray
can never deadlock against a worker thread writing the next status.

**Why it exists as its own module.** The tray reads it, the supervisor writes
it, and the orchestrator client will write it too. Keeping it standalone lets
all three import it without importing each other.

**Why the locking is not incidental.** A torn read shows a stale tray icon.
Nothing raises; the provider simply believes something false about their own
machine. That is exactly the failure class ADR 0002 exists to catch.

| Status | Meaning | Set by |
|---|---|---|
| `STARTING` | Boot, before Ollama is confirmed | `_supervise` |
| `IDLE` | Ready and accepting work | `_supervise`, `on_drain_change` |
| `BUSY` | Serving at least one request | **nothing yet** — waits on leases |
| `DRAINING` | Finishing current work, refusing new | `_supervise`, `on_drain_change` |
| `STOPPED` | Quit | `on_quit` |
| `ERROR` | Ollama missing or unreachable | `_supervise` |

`Status.accepts_work` is `True` for `IDLE` and `BUSY` only.

### 3.2 `agent/app.py` — wiring and supervision

**What.** Builds the four threads, owns the health-poll loop, and defines what
the drain toggle does.

**How.** `_supervise` calls `supervisor.start()` once, then loops every
`HEALTH_POLL_S = 15.0` seconds (`app.py:36`): if Ollama is up, the status
becomes `IDLE` or `DRAINING` depending on the `accepting` event; if not, it
becomes `ERROR`. The loop exits when the `stop` event is set.

**Why 15 seconds.** Slow enough to cost nothing, fast enough that a provider who
kills Ollama sees the tray go red before they wonder whether the app noticed.

**Why `on_drain_change` writes state directly** (`app.py:104`): reflecting the
click immediately instead of waiting out the poll interval. A drain control that
looks unresponsive for fifteen seconds gets clicked again, and then the provider
stops trusting it.

> ⚠ Two real defects live in this file. See §8.1 and §8.2.

### 3.3 `agent/runtime/ollama.py` — the inference runtime

**What.** Locate, start, health-check and stop the Ollama server.

**How.**

- `find_binary()` checks `PATH`, then falls back to
  `%LOCALAPPDATA%\Programs\Ollama\ollama.exe`. The Windows installer writes
  there and does not always reach the `PATH` of an already-open session, so
  `PATH` alone produces false "not installed" results.
- `is_up()` (`ollama.py:65`) is a 2-second `GET /api/tags`.
- `start()` (`ollama.py:71`) returns immediately if a server is already
  reachable, setting `_adopted = True`. Otherwise it spawns `ollama serve` with
  `CREATE_NO_WINDOW` and polls until reachable or the 60-second deadline passes.
- `stop()` (`ollama.py:114`) returns without doing anything if `_adopted`.

**Why the adoption rule is the centre of this module.** Plenty of people who
would rent out a GPU already run Ollama themselves. An agent that terminates
their server on exit — taking their loaded model and their chat session with it
— gets uninstalled the same day. **Never kill an Ollama the provider was already
running.**

**Why the exit-code check sits inside the wait loop** (`ollama.py:98`): a server
that dies in 200 ms — port 11434 already bound is the common case — would
otherwise burn the full 60-second deadline and then report a timeout, hiding the
return code that actually explains the failure.

### 3.4 `agent/winproc.py` — the subprocess boundary

**What.** The only sanctioned way for code inside the app to spawn a process.

**How.** A single `run()` wrapper (`winproc.py:37`), deliberately narrower than
`subprocess.run`: text mode and captured output are not optional, and
`creationflags=CREATE_NO_WINDOW` is always applied.

**Why this module exists at all.** `GPUProvider.exe` is built windowed
(`console=False`), so the app has no console. A child process started without
`CREATE_NO_WINDOW` does not inherit one — Windows allocates a *brand new*
console and shows it. A short-lived probe like `ollama --version` therefore
appears as a black rectangle that flashes on screen and vanishes.

That bug is nasty in two specific ways:

1. **It is invisible from a terminal.** Run from a console, the child inherits
   the parent's console and nothing is created. It only reproduces in the
   packaged app a provider actually installs.
2. **It does not raise.** The probe succeeds, the data is correct, and the only
   symptom is that the app looks broken and untrustworthy on someone else's
   desktop.

So the rule is structural rather than remembered: **nothing inside the app calls
`subprocess` directly.** One documented exception, marked at the call site:
`agent/bench.py`, which is run standalone, must stay copyable onto a rented box
by itself, and is console-only anyway.

`CREATE_NO_WINDOW` degrades to `0` off Windows (`winproc.py:34`) so callers need
no platform check.

### 3.5 `agent/telemetry.py` — one honest snapshot

**What.** Gathers everything a dashboard needs — host, GPU, Ollama, node status
— into plain dataclasses and a JSON-serialisable dict.

**How.**

| Function | Source | Notes |
|---|---|---|
| `detect_host()` | `socket`, `platform`, `os.cpu_count()` | Prefers `PROCESSOR_IDENTIFIER` because `platform.processor()` is empty on some Windows builds |
| `_ram_total_mb()` | `GlobalMemoryStatusEx` via `ctypes` | Windows-only by design; returns `None` elsewhere |
| `detect_gpu()` | `nvidia-smi --query-gpu=...` through `winproc` | Parses `[N/A]` to `None` — laptop and virtualised GPUs commonly omit temperature |
| `detect_ollama()` | `GET /api/tags` + `GET /api/ps` | Two different questions: downloaded vs resident in VRAM |
| `_ollama_version()` | `ollama --version` | `@lru_cache(maxsize=1)` |

**Why every hardware field is `Optional`.** A machine with no NVIDIA GPU is not a
broken machine — it is a machine we cannot rent out. The UI has to be able to
say that calmly instead of showing a traceback. Absence is a normal outcome.

**Why `_ollama_version` is cached** (`telemetry.py:180`): the dashboard polls
every 3 seconds and the version cannot change while the app runs. Spawning a
process on that interval to re-read a constant is real cost on a provider's
machine — and it is precisely how the console flash of §3.4 came back. The trade
is that upgrading Ollama under a running app reports the stale version until
restart; acceptable for a display field, **not** acceptable for anything that
gates behaviour on a version number.

**Why `available` and `loaded` are separate.** `/api/tags` is what has been
downloaded; `/api/ps` is what is resident in VRAM right now. A provider with ten
models pulled and none loaded is idle, and the dashboard must not imply
otherwise.

**Why `rentable` is computed here** (`telemetry.py:87`): a GPU alone is not
enough and a running Ollama alone is not enough. There is one honest answer to
"can I earn money on this box", and computing it in one place keeps every
surface agreeing on it.

**The snapshot contract** — this is the payload crossing the JS bridge:

```jsonc
{
  "host":   { "hostname", "os_version", "cpu", "logical_cores", "ram_total_mb" },
  "gpu":    { "name", "vram_total_mb", "vram_used_mb",
              "utilisation_pct", "temperature_c", "driver" },   // or null
  "ollama": { "reachable", "version",
              "available": [{ "name", "size_mb" }],
              "loaded":    [{ "name", "size_mb" }] },
  "node":   { "status", "detail", "accepts_work" },
  "rentable": true
}
```

### 3.6 `agent/ui/tray.py` — the tray icon

**What.** A coloured dot near the clock, a status line, a drain toggle, and
Quit.

**How.** The icon is a PIL `Image` drawn in code (`tray.py:36`) — a filled
ellipse in one of six colours. The menu's first item is intentionally
`enabled=False` so it reads as a status line rather than something clickable
(`tray.py:71`). "Open dashboard" carries `default=True`, making it the
double-click action — which is what people try first on a tray icon before they
ever find the menu (`tray.py:75`). `state.on_change(refresh)` re-renders the
icon and tooltip on every status change.

**Why the icon is drawn rather than loaded from `.ico`.** That is a packaging
decision. A bundled asset means `--add-data` in the PyInstaller spec and a path
that resolves differently under `sys._MEIPASS` than from source — a recurring
way for a frozen build to break where the source build never does.

**Why the colours are what they are.** They must read at a glance from a 16-pixel
tray slot: green good, blue working, amber transitional, red broken, grey off.

**Why the tray matters at all.** A provider installs this, sees a dot, and should
never need to look at it again — except for the one moment that justifies having
a UI: when they sit down to play a game and want their GPU back.

### 3.7 `agent/ui/window.py` — the desktop dashboard

**What.** A chrome-less native window with its own taskbar entry, rendered by
WebView2, plus the JS↔Python bridge.

**How.**

- `_asset_root()` (`window.py:29`) resolves `desktop.html` under
  `sys._MEIPASS` when frozen and under the repository root from source.
- `Api` (`window.py:45`) is the bridge object. It exposes exactly two methods:
  `snapshot()` and `set_accepting(bool)`.
- `on_closing` (`window.py:81`) hides the window and returns `False`, which
  **cancels the close**.
- `run()` calls `webview.start()`, which blocks until every window is destroyed.

**Why `_MEIPASS` handling is explicit.** PyInstaller unpacks a one-file build to
a temporary directory. Resolving assets relative to `__file__` instead would
land inside the archive path and fail *only* in the packaged app — the worst
possible place to discover it.

**Why closing does not exit.** A provider who clicks the X expects the node to
keep earning from the tray. Closing a dashboard means closing a dashboard.

**Why the `Api` surface is kept small and boring.** It is the only place where
something *rendered* can reach into the process. A method added here is a method
the page can call. Reading telemetry and toggling work acceptance grant the page
no reach the agent did not already have — which is the test that governs both
this class and `agent/requirements.txt`.

**Debugging tip.** `webview.start(func=..., debug=False)` at `window.py:93` —
flip `debug` to `True` to get WebView2 devtools. That is the only way to see JS
errors inside the window.

### 3.8 `agent/ui/web/` and `web-client/src/desktop/DesktopApp.jsx` — the UI

**What.** The compiled React dashboard, and its source.

**How the page talks to Python.** `DesktopApp.jsx:68` calls
`window.pywebview.api.snapshot()` every `POLL_MS = 3000`. It waits on the
`pywebviewready` event when the API is not yet present (`DesktopApp.jsx:87`),
because pywebview injects the bridge asynchronously and reading it on first
paint is a race that usually loses.

**Why bridge failure is rendered separately from node health**
(`DesktopApp.jsx:72`): conflating them would show a green node while the window
is actually blind. The UI says which one broke.

**Why 3 seconds.** Frequent enough that VRAM and utilisation feel live during a
job; cheap enough to be invisible, since a snapshot is one `nvidia-smi` call and
two localhost requests.

**Why cloud models render as `cloud` rather than `0 MB`**
(`DesktopApp.jsx:209`): cloud-hosted entries report zero bytes because they do
not live on this disk, and "0 MB" would read as a corrupt download.

**Why `desktop.html` has no Google Fonts link**, unlike the public
`index.html`: this page loads from disk inside a window that must render
identically with the network unplugged. A remote font would either block first
paint or silently fall back.

### 3.9 `agent/bench.py` — capacity measurement

**What.** A standalone script measuring what a machine is worth as an inference
provider: cold-start time and aggregate throughput at several concurrency
levels.

**How.** For each level it fires N concurrent streamed generations at
`/api/generate` with a fixed prompt and `num_predict=256`, then computes
**total tokens ÷ wall-clock elapsed**. It prints that beside the "uncontended"
figure — the sum of per-request rates — and warns when the two diverge by more
than 1.3×.

**Why wall clock is the measurement and not bookkeeping.** Ollama's
`eval_duration` counts only the time a request spent *generating*, never the
time it spent queued behind another request. Summing per-request rates therefore
describes a parallel server that may not exist. This exact error overstated
aggregate throughput by **4.3×** before it was fixed, and pricing built on an
overstated capacity number inherits the same error. See ADR 0003.

**Why it imports nothing from `agent/`.** It is meant to stay copyable onto a
rented GPU box by itself, where the repository root is not on `sys.path`.

**Why there is no pass/fail threshold.** What counts as acceptable throughput is
a pricing decision, not a measurement. A generated harness asserting the wrong
bound would report success.

```powershell
python agent/bench.py --model qwen2.5:7b --concurrency 1,4,16 --json out.json
```

### 3.10 `agent/core/` — the hand-built half

Three modules, each currently an interface raising `NotImplementedError`. They
are not on the boot path, and that is deliberate: nothing here is urgent, so it
can be written slowly and carefully.

`creds.py` is the exception to "not urgent" as of M1. The provider endpoints
ship unauthenticated under [ADR 0004](adr/0004-m1-unauthenticated-heartbeat.md),
and this module is what retires that ADR. Its header was rewritten after M1 with
the six design questions the milestone actually raised — first credential
issuance, binding the credential to the claimed node_id, recovery when the
registry has lost a node, what to do when `load()` fails mid-run, per-heartbeat
cost, and clean deregistration. **Read the file, not this table.**

| Module | Interface | How it fails silently |
|---|---|---|
| `creds.py` | `load()`, `store()`, `clear()` | A credential stored somewhere readable works *perfectly*. Nothing raises. The machine is simply now a way into the marketplace for anyone with local access |
| `lease.py` | `claim()`, `renew()`, `release()` | An unreleased lease still expires eventually. Meanwhile the scheduler believes a GPU is busy that is idle, and the only symptom is revenue being lower than it should be |
| `meter.py` | `record()`, `pending()`, `acknowledge()` | Undercounting is invisible from the inside: every request succeeds, every customer is happy, the provider is paid too little. Overcounting is worse and equally quiet |

The design notes in each file header are the actual specification. The
load-bearing ones:

- **The credential belongs to the machine, not the person.** Two PCs means two
  credentials, and revoking one must not log out the other. On Windows the
  storage answer is almost certainly DPAPI (`CryptProtectData`, user scope) —
  not a file in `%APPDATA%`, not the registry — because DPAPI ties the
  ciphertext to the Windows account, so copying the file elsewhere yields
  nothing.
- **Drain is not stop.** Drain refuses new work and lets current work finish. A
  provider who wants to play a game will wait a few seconds; they will not wait
  for a queue.
- **The lease deadline must be enforced by the orchestrator**, because the
  failure being protected against is *this machine disappearing*. An expiry
  tracked only here expires only if this code is still running.
- **Make the client timeout longer than the server's slowest honest response.**
  The inverse is what hid an error branch that had never once executed.
- **Crash and unclean shutdown are the normal case.** Gaming PCs get put to
  sleep mid-job.
- **A customer's token must never reach a provider machine.** It terminates at
  the gateway. If a design here needs one, the design is wrong.

### 3.11 `agent/identity.py` — who this machine is

**What.** Produces a stable 32-character `node_id` and persists it under
`%LOCALAPPDATA%\GPUProvider`.

**How.** `sha256(salt + MachineGuid)[:32]`, where MachineGuid is read from
`HKLM\SOFTWARE\Microsoft\Cryptography\MachineGuid` with `KEY_WOW64_64KEY` (a
32-bit Python would otherwise be redirected to the WOW6432Node view and derive a
different id on the same machine). The persisted file wins on read, so the id
survives a Windows reinstall that changes the GUID. Writing it is best-effort:
a machine that cannot write to `%LOCALAPPDATA%` still gets a working id, it just
re-derives it each boot.

**Why hash rather than use the GUID directly.** The MachineGuid is used by other
software as a machine fingerprint. Emitting it into our logs and UI would leak a
correlatable hardware identifier for no benefit.

**Why this is not `agent/core/creds.py`.** A node_id is an *identifier*, not a
*credential* — it appears in URLs, logs and the marketplace UI, and anyone who
learns it can impersonate the node today. Deriving an identifier does not cross
the hand-built boundary; storing a secret does. `creds.py` remains unwritten and
its header is the specification.

### 3.12 `agent/reporter.py` — the heartbeat loop

**What.** Registers this node once, then heartbeats status and live metrics
every `heartbeat_interval_s` (server-dictated, 15s by default) for the life of
the process.

**How.** `register()` sends static hardware; `heartbeat()` sends live state.
The split is deliberate: a heartbeat cannot silently rewrite what GPU this
machine has, because the fields are not in its schema at all.

**Why the loop never returns.** `run()` catches every transport error, logs it,
backs off (capped at 120s) and tries again. This is the direct lesson of §8.1 —
a supervision loop that returns on error leaves a thread that looks alive and a
node that is silently gone. The tests assert the loop survives an orchestrator
that is unreachable from the first request.

**How it self-heals.** A heartbeat for a node the registry does not know returns
404, and the reporter re-registers rather than retrying forever. That is what
makes a wiped or restored database recover on its own instead of leaving every
provider heartbeating into nothing.

**Why the timeout is 15s.** The orchestrator's database connect timeout is 5s,
so its slowest honest response is several seconds. A client timeout shorter than
that turns a working-but-slow server into a permanently failing one — the exact
inversion called out in §9.

**`accepts_work` is an AND, not a copy.** It is `node.accepts_work and
telemetry.rentable`: a provider who has not drained but has no usable GPU still
must not advertise availability. There is a test named for this.

### 3.13 `agent/main.py` — the M0 orchestrator probe

A small script from M0 that reads `ORCHESTRATOR_URL` from `.env` and
distinguishes three outcomes: healthy (exit 0), reachable but unhealthy (exit
1), and unreachable (exit 1). Superseded in practice by the provider app; kept
as the M0 acceptance artifact. See §8.4 for a bug in it.

### 3.14 `orchestrator/main.py` — the control plane today

FastAPI with five endpoints.

| Endpoint | Does |
|---|---|
| `GET /service` | Identifies the service. Works with the database down |
| `GET /health` | Opens Postgres with `connect_timeout=5`, runs `SELECT 1` |
| `POST /providers/register` | Upsert by node_id, returns the heartbeat interval |
| `POST /providers/heartbeat` | UPDATE; 404 if the node is unknown |
| `GET /providers/nodes` | The registry, with liveness computed per row |

**Why the health check touches the database.** A health endpoint that only
proves the web framework is running tells you nothing about whether the service
can do its job. This was the M0 acceptance gate.

**Why register upserts and heartbeat does not.** Registration is idempotent, so
an agent restarting mid-network-retry cannot create a duplicate or lose its
`registered_at`. Heartbeat deliberately refuses to create rows: if it upserted,
a wiped database would silently refill with nodes that never re-enrolled, and
every field the heartbeat does not carry — the entire hardware capability —
would be permanently null.

**Liveness is derived, never stored** (`orchestrator/liveness.py`). There is no
`is_online` column and no background sweeper. A sweeper that dies leaves every
row reading "online" forever with nothing raising; a value computed from
`last_heartbeat_at` at read time cannot lie about a heartbeat it never received.
`never_seen` is kept distinct from `offline` because "registered and never
checked in" is a broken install, while "offline" is usually a sleeping PC.

**Why a failed node read is a 503 and not an empty list.** An empty list is a
valid answer meaning "no providers". Returning it on failure would render as a
marketplace with no supply, which is indistinguishable from the truth and wrong.
The website has a matching rule — see `services/api.js`.

> ⚠ The provider endpoints are unauthenticated. See
> [ADR 0004](adr/0004-m1-unauthenticated-heartbeat.md), which states what an
> attacker can do with them and the conditions under which this must end. The
> orchestrator must not be internet-exposed while that ADR stands.

---

## 4. Dependencies as a security boundary

`agent/requirements.txt` is not just a build input. The agent runs on a
stranger's gaming PC, so anything listed there is something shipped onto
hardware we do not control. The file is short on purpose and pinned with `==`
so every provider machine resolves the same tree.

| Package | Why it is allowed |
|---|---|
| `httpx` | Talks to the orchestrator and to Ollama. Both over HTTP |
| `python-dotenv` | Config only |
| `pystray` + `pillow` | Pure presentation. Pillow is here *because* pystray takes icons as PIL images |
| `pywebview` | Draws the window with WebView2. Ships no browser engine and no HTTP server |

**The rule: no database driver, ever.** If `psycopg` appears in this file, the
design went wrong upstream of the file.

`pywebview` pulls in `pythonnet` to reach WinForms, which is the largest single
addition to the agent's footprint and the one worth re-justifying if it grows.
It passes the test that governs the file because the page can only reach the
process through the two-method `Api` object.

---

## 5. The build pipeline

Two stages, two languages.

```
web-client/  ──npm run build:desktop──▶  agent/ui/web/  ──PyInstaller──▶  GPUProvider.exe
```

```powershell
cd web-client; npm run build:desktop; cd ..
.\packaging\build.ps1
```

### 5.1 Stage one — Vite

`web-client/vite.desktop.config.js` is separate from `vite.config.js` because
the desktop window and the public site disagree on two things that cannot both
be true in one config:

- **`base: './'`** (`vite.desktop.config.js:13`) — the site is served from a
  GitHub Pages subpath; the window is loaded from a `file://` URL, where
  absolute asset paths resolve to the filesystem root and 404 *silently*,
  leaving a blank window with no error anywhere.
- **`outDir: '../agent/ui/web'`** (`:17`) — the bundle has to land inside
  `agent/` because PyInstaller packages the exe from that tree.

`assetsInlineLimit: 0` (`:22`) keeps it to one JS file and one CSS file: a
window loading from disk gains nothing from code splitting, and it makes the
PyInstaller data spec easier to reason about.

> **Gotcha.** `emptyOutDir: true` wipes `agent/ui/web/` on every build, asset
> filenames are content-hashed, and that directory **is tracked in git**. Every
> dashboard rebuild produces a diff with renamed files. Commit it, or the exe
> ships a stale UI.

### 5.2 Stage two — PyInstaller

`packaging/build.ps1` uses `agent\env\Scripts\python.exe` (Python 3.11.15,
gitignored via `*env/`), installs PyInstaller into that virtualenv, runs the
spec with `--noconfirm --clean`, and asserts the exe exists. Output:
`packaging\dist\GPUProvider.exe`, also gitignored. Verified 2026-08-11 at
23.6 MB.

`packaging/GPUProvider.spec` carries four non-obvious decisions:

**The bundle guard** (`spec:16`). The spec aborts the build if
`agent/ui/web/desktop.html` is missing. A missing bundle produces *no runtime
error* — pywebview loads a `file://` URL that does not exist and paints nothing.
Failing the build is the only place this can be caught loudly.

**The pywebview .NET assemblies** (`spec:27-36`). `Microsoft.Web.WebView2.Core.dll`,
`.WinForms.dll`, `WebBrowserInterop.x64.dll` and a per-architecture
`WebView2Loader.dll` are loaded by filesystem path through `clr.AddReference`,
invisible to import analysis. **The layout is not the obvious one:**
`webview/util.py`'s frozen branch looks for the assemblies *flat at
`sys._MEIPASS`*, not under the `webview/lib/` tree they occupy in
site-packages, while `edgechromium.py` appends `sys._MEIPASS\win-x64` (and the
arm64/x86 equivalents) to `PATH` for the loaders. Mirroring the source layout
puts every file where nothing looks, and the symptom is a .NET
`FileNotFoundException` at import time, in the frozen build only.

**`hiddenimports`** (`spec:46`). `pystray._win32`,
`webview.platforms.winforms`, `webview.platforms.edgechromium` are all selected
at runtime *by string* — pystray from the platform, pywebview by walking a list
of `import_*` functions in `guilib.py` — so static analysis finds none of them.

**`excludes=[]`** (`spec:59`). `agent.core` is absent from the current build
simply because nothing imports it yet — import-graph analysis doing its job, not
an exclusion. Naming those modules in `excludes` would make the frozen build
raise `ImportError` at exactly the moment the source build started working. **A
packaging config must not be what decides which modules the application may
import.**

**`upx=False`** (`spec:80`). Executable packers are among the strongest
heuristic triggers for antivirus detection, and this app's entire distribution
problem is being flagged by Defender and SmartScreen. Trading a few megabytes
for a detection that then has to be appealed is a bad trade. Do not enable it
without measuring detection rate both ways. Full context, including the cost
table for code-signing options, is in `packaging/README.md`.

### 5.3 Reading process memory correctly

A one-file build runs as **two processes**: the bootloader parent, roughly 8 MB,
which owns no window and whose `MainWindowTitle` is always empty; and the child
that runs Python and owns the "GPU Provider" window at roughly 121 MB. WebView2
spawns further helper processes not counted in either. Checking only the parent
makes the app look far lighter than it is and makes a working build look broken.

---

## 6. Running and debugging from source

```powershell
cd C:\Users\rusha\Startup
python -m agent.app          # console attached; print() output visible
```

Running from a terminal is the only way to see the `[app]` lines — and, as §3.4
explains, it is also the configuration in which the console-flash bug cannot
reproduce. Confirm window-related fixes against the packaged exe, not the source
run.

For the dashboard's own errors, set `debug=True` at `window.py:93`.

---

## 7. Failure playbook

| Symptom | Cause | Where to look |
|---|---|---|
| Window opens blank, no error anywhere | Missing bundle, or `base` is not `'./'` | `vite.desktop.config.js:13`, `spec:16` |
| .NET `FileNotFoundException` on launch | WEBVIEW_DATAS layout wrong | `spec:27-36` |
| Black console box flashes periodically | A `subprocess` call bypassing `winproc` | `agent/winproc.py` |
| Tray red, "Ollama stopped responding" | `is_up()` returning `False` | `ollama.py:65` |
| `'ollama serve' exited immediately` | Port 11434 already owned | `ollama.py:98` |
| exe raises `ImportError` the source run does not | Module selected at runtime by string | `spec:46` |
| Process survives Quit | `dashboard.destroy()` not reached | `app.py:131` |
| Dashboard shows "Lost contact with the agent" | Bridge broke, not the machine | `DesktopApp.jsx:72` |
| Tray green on a machine with no Ollama | §8.1 + §8.2 below | `app.py:49`, `tray.py:55` |
| Node missing from the website's table | Agent not enrolled, or wrong `ORCHESTRATOR_URL` | `reporter.py`, agent log `[reporter]` lines |
| Node stuck "offline" while the app runs | Heartbeats failing; the loop retries silently | agent log, `GET /providers/nodes` |
| Website shows "Cannot reach the orchestrator" | Control plane down — deliberately not an empty table | `services/api.js` |
| Defender flags the release | Expected for unsigned one-file builds | `packaging/README.md` |

---

## 8. Known defects and open edges

Found by reading the code on 2026-08-11. §8.1, §8.2 and §8.4 are **still open**.
§8.3 was fixed during M1 and is kept here with what changed, because the trap it
describes is easy to reintroduce.

### 8.1 The supervisor thread dies permanently if Ollama is absent
`agent/app.py:49` — `_supervise` catches `OllamaError`, sets `ERROR`, and
**returns**. There is no retry. A provider who installs Ollama afterwards must
restart the app; nothing ever re-checks. *Hand-built territory: it degrades
without raising.*

### 8.2 That compounds into a false-green node
`agent/ui/tray.py:55` — the tray's `accepting()` reads
`state.status.accepts_work` rather than the `accepting` event, so in `ERROR` the
checkbox reads unchecked. Clicking it calls `on_drain_change(True)`, which sets
`IDLE / "ready for work"` (`app.py:104`). Normally the supervisor corrects that
within 15 seconds — **but if the thread already exited via §8.1, nothing ever
does.** The node claims it is ready for work with no inference runtime at all.

### 8.3 `models()` advertised cloud models this machine cannot serve — FIXED
`agent/runtime/ollama.py` returned every name from `/api/tags`, including Ollama
Cloud entries, which are ~400-byte pointers carrying
`"remote_host": "https://ollama.com:443"`. M1 made this live: enrolment now
advertises a model list, so the node would have claimed capacity it does not
have, and work scheduled against that claim would be proxied to ollama.com on
the provider's own account.

Now filtered in three places, on the presence of `remote_host` rather than on a
size heuristic: `runtime/ollama.py::models()`, `telemetry.py::_model()` (which
sets `Model.remote`), and `reporter.py::metrics_payload()` (which drops them
before they reach the wire).

**The reintroduction risk is the reason this entry stays.** A future call site
that reads `/api/tags` directly gets the unfiltered list back, and nothing
raises — the node simply advertises models it cannot serve. Note also that the
filter proves only that weights are *on disk*: it is not model-residency logic,
which is hand-built, and must not be used as a scheduling input.

### 8.4 `agent/main.py` crashes instead of reporting when the URL is unset
`agent/main.py:8` does not check `os.getenv("ORCHESTRATOR_URL")` for `None`, so
`url + "/health"` raises `TypeError`, which `except httpx.RequestError` does not
catch. You get a traceback instead of the intended message.

### 8.5 Smaller edges
- `Status.BUSY` is defined and coloured but never set by anything. It waits on
  leases.
- `icon.stop()` runs twice on quit — once in `quit_app`, once after
  `window.run()` returns. Benign, but it is redundancy, not intent.
- `GET /health` no longer catches bare `Exception` (a genuine bug now surfaces
  as a 500 rather than masquerading as "degraded"), but the *response* still
  collapses "DATABASE_URL is unset" and "database is unreachable" into the same
  `{"status":"degraded","db":"down"}`. The provider endpoints do distinguish
  them, in the 503 detail.
- A provider who quits is not deregistered; the orchestrator ages them out by
  TTL instead. Up to 120s of advertised capacity that has gone. Closing this
  needs a credential — see `agent/core/creds.py`, design question 6.

---

## 9. Invariants — do not break these without a new ADR

1. **Never kill an Ollama the provider was already running.** (`ollama.py`)
2. **Nothing inside the app calls `subprocess` directly.** Use `winproc`.
   (`winproc.py`)
3. **No database driver in `agent/requirements.txt`. Ever.**
4. **A customer token never reaches a provider machine.** It terminates at the
   gateway.
5. **The `Api` bridge surface stays small.** Every method added is a method the
   rendered page can call.
6. **Capacity claims come from wall-clock measurement**, never from summed
   per-request rates. (`bench.py`, ADR 0003)
7. **The packaging config never decides what the app may import.**
   (`excludes=[]`)
8. **UPX stays off** until someone measures detection rate both ways.
9. **Absence of hardware is a normal outcome, not an error.** Every
   hardware-dependent telemetry field is `Optional`.
10. **Liveness is derived from the last heartbeat, never stored.** No
    `is_online` column, no sweeper. (`orchestrator/liveness.py`)
11. **A failed read is never rendered as an empty fleet.** Not in the API, not
    in the UI. Absent renders as `—`, never as `0`.
12. **A node never advertises capacity it cannot serve.** Cloud models are
    filtered; `accepts_work` requires both provider consent and a usable GPU.
13. **The client timeout is longer than the server's slowest honest response.**
14. **If it is wrong, will something reliably raise?** If not, it is hand-built.
    (ADR 0002)

---

## 10. Related documents

- [ADR 0002 — what we generate and what we hand-build](adr/0002-generated-vs-handbuilt.md)
- [ADR 0003 — inference as the beachhead market](adr/0003-inference-beachhead.md)
- [`packaging/README.md`](../packaging/README.md) — build details, Defender and SmartScreen
- [`agent/core/README.md`](../agent/core/README.md) — the hand-built package
- [`README.md`](../README.md) — repository quick start
