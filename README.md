# P2P Compute Marketplace

A decentralized marketplace for GPU compute, on two tracks:

- **Cloud Gaming** — low-latency streamed sessions
- **General Compute** — batch jobs (render, media, model inference)

Providers rent out idle GPUs; the orchestrator matches them to demand.

---

## What actually runs today

The backend is being rebuilt in Python. Two stacks exist in this repo and only
one of them is live — check this table before you run anything.

| Path | Language | Status |
|---|---|---|
| `orchestrator/` | Python + FastAPI | **live** — this is the control plane |
| `agent/` | Python | **live** — provider-side health check |
| `web-client/` | React + Vite | **live** |
| `services/` | TypeScript | **frozen** — read-only contract reference, do not run |
| `packages/contracts/` | TypeScript | **frozen** — Zod schemas the Python side must match |

Current working milestone is a **local rented-inference vertical slice**:
Postgres stores provider heartbeats, the orchestrator issues customer API
keys, and an authenticated chat request is routed to one configured provider's
local Ollama model. This proves the flow on one machine; it is not yet a secure,
internet-facing marketplace. See [docs/Tasks/tasks.md](docs/Tasks/tasks.md).

---

## Quick start (Windows)

Everything below is PowerShell, run from the repository root.

### 0. Prerequisites

- **Docker Desktop**, running
- **Python 3.11** — not 3.12 or 3.13

  The 3.11 pin is not arbitrary: CI runs 3.11 and `.ruff.toml` targets `py311`.
  On a different minor version you can pass locally and fail in CI on syntax
  the two versions disagree about. Install from
  [python.org](https://www.python.org/downloads/release/python-3119/) and let
  it register with the launcher, then confirm:

  ```powershell
  py -3.11 -V
  ```

  If that says *"No suitable Python runtime found"*, the launcher can't see a
  3.11. Either install it, or use [uv](https://docs.astral.sh/uv/) which
  fetches its own:

  ```powershell
  uv venv --python 3.11 orchestrator\env
  ```

### 1. Create your `.env`

```powershell
Copy-Item .env.example .env
```

Open `.env` and set a real `POSTGRES_PASSWORD`.

> **The password appears twice, and the two copies are not identical.**
>
> `POSTGRES_PASSWORD` stays **raw** — Docker reads it directly.
> The copy inside `DATABASE_URL` must be **percent-encoded**, because it sits
> inside a URL. If your password contains `@ : / ? # [ ] %`, pasting it raw
> corrupts the URL: libpq splits at the *first* `@`, so the tail of your
> password becomes part of the hostname and you get
>
> ```
> OperationalError: failed to resolve host '<tail-of-password>@localhost'
> ```
>
> which reads like a DNS or Docker fault and is neither. Encode it with:
>
> ```powershell
> python -c "from urllib.parse import quote; print(quote(input(), safe=''))"
> ```
>
> `@` → `%40`, `:` → `%3A`, `/` → `%2F`, `#` → `%23`, `%` → `%25`.

`.env` is gitignored. Never commit it.

### 2. Start Postgres

```powershell
docker compose up -d db
```

> **`db` is not optional — do not run bare `docker compose up`.**
>
> `docker-compose.yml` still describes the frozen TypeScript stack. Its
> `orchestrator` service is `image: node:20` bound to **port 8080** — the same
> port the Python app wants. Bring the whole file up and a Node process takes
> the port, and the bind error you get will not mention Docker anywhere.

Confirm it came up healthy (this takes a few seconds — `starting` is normal at
first):

```powershell
docker ps --filter name=marketplace_db
```

You want `Up ... (healthy)`.

### 3. Run the orchestrator

First time only:

```powershell
py -3.11 -m venv orchestrator\env
.\orchestrator\env\Scripts\python.exe -m pip install -r orchestrator\requirements.txt
```

Every time:

```powershell
.\orchestrator\env\Scripts\python.exe -m uvicorn orchestrator.main:app --reload --port 8080
```

Leave it running. `--reload` restarts it when you edit a file.

> Run this from the **repository root**, not from inside `orchestrator\`. It
> used to be `main:app --app-dir orchestrator`; M1 split the orchestrator into
> several modules that import each other, so it is now a package, like `agent`
> already was. `--app-dir` would put `orchestrator\` itself on the path and the
> intra-package imports would fail.

On boot it creates the `provider_nodes` table if it is missing and prints
`[orchestrator] schema applied`. If the database is down it says so and starts
anyway — `/health` will report `degraded` and the provider endpoints return
`503` until Postgres is back.

Check it from a **second** terminal:

```powershell
Invoke-RestMethod http://localhost:8080/health
```

```json
{ "status": "ok", "db": "ok", "version": "0.1.0" }
```

Interactive API docs: <http://localhost:8080/docs>

### 4. Run the agent

The agent gets its **own** virtualenv. This is deliberate — it ships to a
provider's machine, and its dependency list is a statement about what that
machine is allowed to touch. It has `httpx` and `python-dotenv` and no
database driver, because the agent talks to the orchestrator over HTTP and
must never reach the database.

First time only:

```powershell
py -3.11 -m venv agent\env
.\agent\env\Scripts\python.exe -m pip install -r agent\requirements.txt
```

Every time:

```powershell
.\agent\env\Scripts\python.exe agent\main.py
```

```
http://localhost:8080
Orchestrator Healthy
```

### 5. Verify it end to end

The agent is a health check, so the way to trust it is to watch it fail. Run
each of these and check the exit code with `$LASTEXITCODE`:

| Do this | Expected output | Exit |
|---|---|---|
| Everything running | `Orchestrator Healthy` | `0` |
| `docker stop marketplace_db` | `Orchestrator Reachable but Unhealthy 503` | `1` |
| Stop uvicorn (Ctrl+C) | `Down [WinError 10061] ... actively refused it` | `1` |

Restart with `docker start marketplace_db`. The orchestrator recovers on its
own — it opens a connection per request, so you do **not** need to restart
uvicorn.

Those three cases are different failures and the agent reports them
differently on purpose. `503` means the orchestrator is alive and *its*
database is gone. `10061` means the orchestrator process itself isn't there.
An agent that collapses both into "error" tells you nothing at 2am.

### 6. Enrol this machine as a provider (M1)

`agent\main.py` above is the M0 probe: one health check, then it exits. The
real provider app registers itself and then reports in on a loop.

```powershell
.\agent\env\Scripts\python.exe -m agent.app
```

It starts Ollama if it is not already running, puts an icon in the system
tray, opens the dashboard, and starts a `reporter` thread that calls
`POST /providers/register` once and `POST /providers/heartbeat` every 15
seconds. Watch the console for:

```
[reporter] registered b206e1c7… with http://localhost:8080 (heartbeat every 15s)
```

Then look at the registry:

```powershell
# The registry needs a session: every row describes a real machine, so it is
# not served anonymously. Log in first and reuse the token.
$s = Invoke-RestMethod -Method Post http://localhost:8080/v1/auth/login `
  -ContentType application/json `
  -Body (@{ email = 'you@example.com'; password = 'your-password' } | ConvertTo-Json)

(Invoke-RestMethod http://localhost:8080/providers/nodes `
  -Headers @{ Authorization = "Bearer $($s.token)" }).nodes |
  Select-Object hostname, liveness, accepts_work, last_heartbeat_at
```

If this deployment has `SIGNUPS_OPEN=false`, there is no signup form to make
that account with — create one directly instead:

```powershell
python -m orchestrator.seed_users you@example.com
```

The same data drives the **Nodes** tab of the provider console in
`web-client` (`npm run dev`, then `/app/provider`). There is no mock behind it
any more — if the orchestrator is down the page says so rather than showing
invented hardware.

**Things worth knowing before you debug it:**

- `liveness` is computed from `last_heartbeat_at` on every read, never stored.
  A node goes `offline` after `PROVIDER_TTL_MS` (default 120s) with no
  heartbeat, and `never_seen` means it registered but its heartbeat loop never
  ran — a broken agent, not a sleeping machine.
- The node id lives in `%LOCALAPPDATA%\GPUProvider\node_id`. Delete it and the
  machine enrols as a new node. It is derived from the Windows MachineGuid, so
  it survives reinstalls. It is an identifier, **not** a credential — see
  `docs/adr/0004-m1-unauthenticated-heartbeat.md` for why the endpoint takes
  anyone's word for it in M1 and what has to change before M2.
- `accepts_work` is false unless the machine has an NVIDIA GPU *and* Ollama is
  answering, no matter what the tray toggle says. A node that cannot serve must
  never advertise that it can.
- Ollama Cloud models are filtered out of `local_models`. They appear in
  `/api/tags` looking exactly like local weights but are ~400-byte pointers to
  ollama.com.
- Kill the orchestrator while the agent runs. The agent must keep retrying with
  backoff and reconnect on its own; it should never need restarting.

### 7. Run rented inference

Inference runs **on the provider's machine**, not on the orchestrator. The
orchestrator queues a job for a chosen node; that node's agent claims it over a
connection it opened itself, runs it against its own Ollama, and posts the
result back. That direction matters: a provider's PC sits behind a home router
with no address the server could dial.

There is no longer a `LOCAL_DEMO_MODE`, a `DEMO_PROVIDER_NODE_ID`, or a
`LOCAL_OLLAMA_URL` on the orchestrator. Any online provider that advertises the
model is eligible, and API keys belong to a real account instead of to whoever
reached the box from localhost.

**Create an account and a key.**

```powershell
$body = @{ email = "you@example.com"; password = "a-long-enough-password" } | ConvertTo-Json
$session = Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/auth/signup `
    -ContentType application/json -Body $body
$headers = @{ Authorization = "Bearer $($session.token)" }

$key = Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/api-keys `
    -ContentType application/json -Headers $headers -Body (@{ name = "my key" } | ConvertTo-Json)
$key.key    # shown once, never retrievable again
```

**Start a provider.** Run the agent (`python -m agent.app`). On registration it
receives a node credential, saves it beside its node id in `%LOCALAPPDATA%`, and
its worker thread begins asking for work. The tray's drain toggle stops new
claims immediately.

**Send a request.** Base URL is `http://localhost:8080/v1`, so any
OpenAI-compatible client works:

```powershell
$body = @{
    model = "tinyllama:latest"
    messages = @(@{ role = "user"; content = "hello" })
} | ConvertTo-Json -Depth 4
Invoke-RestMethod -Method Post -Uri http://localhost:8080/v1/chat/completions `
    -ContentType application/json -Headers @{ Authorization = "Bearer $($key.key)" } -Body $body
```

The provider receives the model and the messages, and nothing else — the
customer's key terminates at the orchestrator and is never forwarded.

**Run the failure cases too.** They are the half worth seeing:

- Toggle the tray to draining, then send a request → `503`, no provider
  accepting.
- Ask for a model no provider has → `404`.
- Stop the agent mid-request → `504` after `DISPATCH_WAIT_SEC`, and the job
  stays queued rather than being lost. Restart the agent and it is picked up.
- Restart the agent → its credential rotates, and the previous one stops
  working.

The demo intentionally lacks provider authentication, TLS, sandboxing,
payments, rate limits, multi-provider scheduling, and failover. Do not expose
it to the public internet.

### 8. Run the tests

```powershell
.\orchestrator\env\Scripts\python.exe -m pytest orchestrator/tests agent/tests -q
.\orchestrator\env\Scripts\python.exe -m ruff check .
```

Neither suite needs Postgres, a network, or the desktop GUI libraries — that is
a hard constraint, because CI has none of them. If you write a test that needs
a live database, it will pass locally and never run again.

---

## Troubleshooting

**`GET /health` takes ~10 seconds when the database is down.**
Expected. `connect_timeout` is applied **per resolved address**, not as a total
budget — `localhost` resolves to both `::1` and `127.0.0.1`, so a 5s timeout
costs 10s worst case. Budget for `connect_timeout × address count`, or connect
to a literal IP.

**`GET /health` hangs forever instead of failing.**
A network call somewhere is missing a timeout. Docker's port proxy keeps
accepting TCP connections after the container stops but never answers, so the
client waits indefinitely and the `except` block is never reached. Every
network call needs an explicit timeout.

**`httpx.ReadTimeout` from the agent while the orchestrator is up.**
The agent's client timeout is shorter than the orchestrator's worst case, so
it hangs up before the `503` arrives. The agent's timeout must exceed
`/health`'s slowest path.

**`[WinError 10061] ... actively refused it`.**
Nothing is listening on that port. Check the orchestrator is running and that
`ORCHESTRATOR_URL` in `.env` matches the port uvicorn actually bound — a stale
`8000` against a server on `8080` produces exactly this.

**`Activate.ps1 cannot be loaded because running scripts is disabled`.**
PowerShell execution policy. Either call the venv's `python.exe` by path as
shown above (which avoids activation entirely), or:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

**Port 8080 already in use.**
Usually the frozen Node orchestrator from a bare `docker compose up`. Find it:

```powershell
netstat -ano | Select-String ":8080" | Select-String "LISTENING"
```

---

## Repository layout

```
orchestrator/      FastAPI control plane            (live)
agent/             provider-side health check       (live)
web-client/        React + Vite frontend            (live)
services/          TypeScript baseline              (frozen)
packages/contracts Zod schemas + shared types       (frozen)
scripts/           developer tooling
docs/              plans, roles, architecture, tasks
```

### The frozen TypeScript baseline

`services/` and `packages/contracts/` are the original Express implementation.
They stay in the tree as a **contract reference** until the Python side reaches
parity — read them, don't run them, don't extend them.

One contract difference matters right now: the TypeScript service returns
`{ok, providers, jobs}` from its health endpoint. The Python orchestrator
returns `{status, db, version}`, and the frontend codes against the Python
shape. Do not copy the TypeScript response.

See [docs/PYTHON-FASTAPI-BACKEND-MIGRATION.md](docs/PYTHON-FASTAPI-BACKEND-MIGRATION.md)
before changing or removing anything under `services/`.

---

## Contributing

Ownership is per-path in [.github/CODEOWNERS](.github/CODEOWNERS); who owns
what and why is in [docs/ROLES.md](docs/ROLES.md) and
[docs/TEAM-EXECUTION-PLAN.md](docs/TEAM-EXECUTION-PLAN.md).

Work on a branch and open a PR — `main` requires the CI gate to be green.
`scripts/ship.ps1` does push → open PR → queue auto-merge in one command:

```powershell
.\scripts\ship.ps1
```

The merge is *queued*, not forced: GitHub holds it until required checks pass.
A red PR merged by hand is how `main` broke on 2026-08-10.

> **`orchestrator/` and `agent/` are a solo build during M0** — a deliberate
> learning exercise. Parallel non-blocking work for everyone else is in
> TEAM-EXECUTION-PLAN.md §7, and none of it touches those two directories.

---

## Documentation

| Document | What it's for |
|---|---|
| [docs/Tasks/tasks.md](docs/Tasks/tasks.md) | Current milestone, task-by-task status |
| [docs/TEAM-EXECUTION-PLAN.md](docs/TEAM-EXECUTION-PLAN.md) | Who does what, in what order, by when |
| [docs/ROLES.md](docs/ROLES.md) | Role definitions and assignments |
| [docs/PYTHON-FASTAPI-BACKEND-MIGRATION.md](docs/PYTHON-FASTAPI-BACKEND-MIGRATION.md) | Contract-first TypeScript → Python plan |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Component boundaries and sequence flows |
| [docs/API.md](docs/API.md) | Endpoint reference and validation behaviour |
| [docs/OPERATIONS.md](docs/OPERATIONS.md) | Runbook, Docker usage, security checklist |
| [docs/UNIFIED-GPU-MARKETPLACE-PLAN.md](docs/UNIFIED-GPU-MARKETPLACE-PLAN.md) | Long-range product plan |
| [docs/LEGAL-STARTER-INDIA.md](docs/LEGAL-STARTER-INDIA.md) | India compliance map |
| [docs/LEGAL-SECURITY-REQUIREMENTS-INDIA.md](docs/LEGAL-SECURITY-REQUIREMENTS-INDIA.md) | Launch-readiness security controls |

---

## After M0

1. `ProviderNode` table + migration
2. `POST /providers/register` and `POST /providers/heartbeat`
3. Agent heartbeat loop, stale → offline via TTL
4. Frontend reads real provider data, mock deleted
5. Security review of the unauthenticated heartbeat endpoint
