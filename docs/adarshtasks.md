# Task List — @AdarshNarwankar

**Roles:** R8 Frontend + R7 Payments *(when payments start — not yet)*
**Owns:** `web-client/`
**Related:** [TEAM-EXECUTION-PLAN.md](TEAM-EXECUTION-PLAN.md) · [ROLES.md](ROLES.md) · [Tasks/tasks.md](Tasks/tasks.md)

Status values: `pending` · `in_progress` · `blocked` · `done`

---

## Current priority

**A1 — the health indicator.** It is the first place the frontend stops being
a mock and starts telling the truth about a real system. Everything else on
this list is maintenance or waits on M1.

---

## The one contract rule

`/health` returns **`{status, db, version}`**.

```json
{ "status": "ok", "db": "ok", "version": "0.1.0" }
```

The frozen TypeScript service in `services/` returns `{ok, providers, jobs}`.
**Do not copy it.** It is a read-only reference for a migration, it is not
running, and it never will be again. `web-client/src/services/api.js` already
targets the correct shape — keep it that way.

---

## A0 — Track 0: first PR · `pending`

Two things, one PR:

1. Add yourself a line in `CONTRIBUTORS.md`. The file does not exist yet —
   creating it is the task.
2. Confirm the frontend builds for someone who is not its author:

   ```powershell
   cd web-client
   npm ci
   npm run build
   ```

`npm ci` — not `npm install`. `ci` installs exactly what the lockfile says and
fails if `package.json` and the lockfile disagree; `install` quietly rewrites
the lockfile to make the disagreement go away. CI runs `ci`, so that is what
you want to reproduce.

**Nobody writes a feature until their first PR is merged.**

- [ ] `CONTRIBUTORS.md` line
- [ ] `npm ci && npm run build` passes locally
- [ ] PR merged

---

## A1 — Orchestrator health indicator · `pending` · **start here**

### Where this actually stands

The execution plan (§8) says `checkOrchestratorHealth` falls back to the wrong
shape. **That is out of date** — it was fixed and now targets `{status, db,
version}` correctly. What remains true is the more interesting half:

```
$ grep -rn "checkOrchestratorHealth" web-client/src/
web-client/src/services/api.js:145:export async function checkOrchestratorHealth() {
```

One hit — the definition. **Nothing calls it.** It is dead code that has never
executed against anything.

### There is a real bug in it, and it is the same bug the agent had

`api.js:146-147`:

```js
const controller = new AbortController();
const timeout = setTimeout(() => controller.abort(), 2000);
```

**Two seconds.** Measured behaviour of the Python orchestrator:

| Database | `/health` responds in |
|---|---|
| up | ~0.4s |
| **down** | **~10s** |

The 10s is not slowness. `connect_timeout` is applied **per resolved address**,
and `localhost` resolves to both `::1` and `127.0.0.1`, so a 5s timeout costs
10s worst case.

So when the database goes down — the exact moment this indicator exists for —
the fetch aborts at 2s, falls into `catch`, and the UI reports
**`unreachable`**. The orchestrator is fine. Its database is not. Your
indicator will point at the wrong system, confidently, every time.

The provider agent hit this identical bug two days ago: a 5s client timeout in
front of a ~10s server response made its `503` branch look correct while never
once executing. Raise the timeout above the server's worst case — 15s.

**Verify it the way the agent was verified:** run the orchestrator, then
`docker stop marketplace_db`, and watch what your indicator says. If it says
"unreachable", it is still wrong.

### Three states, not two

`/health` can answer three different things, and they need three different
treatments in the UI:

| Condition | Response | What it means | UI |
|---|---|---|---|
| `200` | `{status:"ok", db:"ok"}` | Everything works | green |
| `503` | `{status:"degraded", db:"down"}` | **Orchestrator alive, its DB is down** | amber — degraded, *not* offline |
| fetch throws | — | Orchestrator unreachable | red |

The middle one is the whole point. A `503` is not a transport failure — it
carries a meaningful JSON body, and the existing code is right to parse it
rather than discard it. Collapsing "degraded" into "offline" throws away the
half of the signal that tells you where to look.

### Behind a feature flag

Ship it disabled by default. M0 is code complete but not yet verified, and the
frontend should not start depending on a backend contract that is still being
signed off. Flag it, merge it, turn it on once M0 is signed off.

Point it at a running backend with `web-client/.env.local`:

```
VITE_ORCHESTRATOR_URL=http://localhost:8080
```

Run the backend yourself with the README's quick start — you need something to
point at, and running it once teaches you more about the contract than reading
about it.

- [ ] Timeout raised above the server's worst case
- [ ] Three visual states, `degraded` distinct from `unreachable`
- [ ] Called from somewhere real, behind a flag, default off
- [ ] Verified against a live orchestrator **with the database stopped**
- [ ] No polling loop faster than the slowest possible response

---

## A2 — Tailwind CSS 4 migration · `pending` · [#14](https://github.com/RUSHAB3979/Decentralized-Network/issues/14)

`tailwindcss` is pinned back to `^3.4.17`. A 4.x bump broke `main` on
2026-08-10 — the PostCSS plugin moved to `@tailwindcss/postcss` and
`postcss.config.js` still declared the old one.

Four things change at once: the PostCSS package, the `@tailwind` directives in
`index.css`, the config format (`@theme` in CSS), and some default utility
values. The last one is why a green build is not sufficient evidence — compare
the rendered pages before merging.

Details in the issue. Not urgent; `main` builds fine today.

---

## A3 — React 19 + lucide-react 1.x · `pending` · [#17](https://github.com/RUSHAB3979/Decentralized-Network/issues/17)

Dependabot #6 tried all three majors at once and failed:

```
[MISSING_EXPORT] "Github" is not exported by lucide-react
  src/components/AuthPage.jsx:2:53
```

**Do them as two PRs**, `lucide-react` first, then React. Together, any
breakage has two candidate causes and you bisect by hand. Note that `Github`
was simply the *first* error the bundler reached — expect more renamed icons
in files it never got to.

Not urgent.

---

## A4 — Wire the provider list to real data · `blocked` (needs M1)

The M1 payoff. `POST /providers/register` and `/providers/heartbeat` land
first; then the frontend reads live providers and **the corresponding mock is
deleted in the same PR**.

Deleting it matters. A mock left beside real data becomes the thing someone
tests against by accident six months later.

`MOCK_CATALOG` in `api.js` and `marketplaceData.js` are the current mocks.
Only the provider-shaped parts go in M1 — the catalog stays until there is a
real catalog endpoint.

- [ ] Provider list reads live data
- [ ] Mock deleted, not commented out or flagged off
- [ ] Empty state and error state both designed — an empty marketplace is the
      normal case on day one, not an edge case

---

## A5 — Payments (R7) · `pending` — **do not start**

Yours when payments start. They have not started, and starting early means
building against a marketplace that does not yet have providers, sessions, or
a price. Listed so you know it is coming.

---

## A6 — Wire `RenderJobPage.jsx` to the real API · `pending` — **blocked on the render endpoints**

The page already exists at `web-client/src/components/app/RenderJobPage.jsx`,
routed from `App.jsx:89` as `/app/render`. **The form is done — do not rebuild
it.** Blender version, engine, frame range, output format, region, GPU profile
and spending limit are all there. What is missing is that nothing leaves the
browser: the file input is labelled `Sandbox · no upload`, and submitting shows
a hard-coded job id, `render_preview_01`.

[ADR 0006](adr/0006-render-batch-jobs.md) defines the flow. It is three calls,
not one, and the middle one is the reason:

1. `POST /v1/render/jobs` → `202` with a `job_id` and a **presigned PUT URL**
2. `PUT` the `.blend` **straight to object storage** — not to our API
3. `POST /v1/render/jobs/{id}/uploaded` → the orchestrator verifies the object
   and fans the job out into frames

- [ ] All three steps, in `web-client/src/services/renderApi.js`. New file,
      alongside `inferenceApi.js` and `authApi.js`, following whatever those two
      already do for base URL and auth — do not invent a fourth convention
- [ ] The upload uses `XMLHttpRequest` or a fetch with a progress stream so the
      user sees a percentage. A silent five-minute wait on a 400 MB file reads
      as a broken page, and people close the tab
- [ ] The presigned URL is short-lived. Decide and handle what the UI does when
      it expires mid-upload — a retry that re-requests a URL, or a clear message.
      Silently failing at 90% is the bad outcome
- [ ] Upload failure leaves the job visibly at `awaiting_upload`, not "submitted"
- [ ] **Delete the invented rates.** `previewRate` is currently 0.18 / 0.38 /
      0.72 per hour and those numbers came from nowhere

**On the price, read this before touching it.** The page's quote is labelled
`Illustrative only`. ADR 0006 is explicit that those labels come off when
metering lands and *not one commit before* — `agent/core/meter.py` still raises
`NotImplementedError`, so there is no measured price to show. Until there is,
either keep the label exactly as prominent as it is now, or show no number at
all. The failure mode is not a wrong price; it is a screenshot of an invented
price that somebody repeats as a fact. This is the same rule
`ProviderConsolePage.jsx` already follows with its `Live` / `Preview` badges.

---

## A7 — Render job list and detail · `pending` — **blocked on A6**

Once a job can be submitted it has to be watchable, and a render runs for
minutes to hours. There is no synchronous path and never will be — the customer
does not wait on a socket for this.

- [ ] A list at `/app/render/jobs`: status, frame progress, submitted time
- [ ] A detail view showing **per-frame** state. The frame is the unit of work
      under ADR 0006, so "94 of 120 done, 2 failed and retrying" is the honest
      display and a single percentage bar is not
- [ ] Artifact download via presigned GETs from
      `GET /v1/render/jobs/{id}/artifacts`
- [ ] Cancel, wired to `DELETE /v1/render/jobs/{id}`, with the confirmation
      making clear that frames already rendering will finish and are billable
- [ ] Polling with a sane interval and a stop condition. A tab left open
      overnight on a completed job must not still be polling in the morning
- [ ] The empty state is the normal case on day one, as in A4

**Note on scope.** During the pilot, renders run only on nodes explicitly
flagged `render_eligible`, which means one machine — the founder's. A job can
therefore sit `queued` for a long time with nothing wrong. The UI should say
"waiting for an available renderer" rather than implying failure or, worse,
showing an estimated start time it cannot know.

---

## Notes

Add a dated line when something changes.

| Date | Note |
|------|------|
| 2026-08-10 | File created. Corrected §8's claim about `checkOrchestratorHealth`: the response shape was already fixed; the function is dead code with a 2s timeout in front of a ~10s worst-case response. |
| 2026-08-18 | **Two tasks added, A6 and A7**, from [ADR 0006](adr/0006-render-batch-jobs.md) — Blender batch rendering as a second workload class. Both are blocked on orchestrator endpoints that do not exist yet, so **A1 is still the current priority** and nothing here changes that. A6 is deliberately written as "wire the page that already exists" — `RenderJobPage.jsx` is a complete form and rebuilding it would be waste. |
