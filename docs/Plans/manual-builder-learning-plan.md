# Manual Builder Learning Roadmap

## Build the Marketplace by Learning Each Necessary Layer

**For:** solo founder writing every line of product code manually  
**Method:** learn a narrow concept → build one bounded proof → explain it → pass the gate → move on  
**Rule:** Do not study technologies that the next gate does not require. Do not begin media, payments, public Providers, or compute early.

This roadmap follows the decision-gated product plan in [`plan.md`](./plan.md). It is not a generic computer-science curriculum: every topic exists because the product will require it.

---

## 1. How to use this roadmap

### Your learning loop

For every phase:

1. Read the official documentation until you can explain the model in your own words.
2. Build the listed exercise manually from a blank file. Do not copy a completed tutorial project.
3. Break it deliberately: invalid input, missing config, process crash, duplicate request, network timeout.
4. Write a short note: what failed, what state existed, and how your design recovered.
5. Show the code/result for review before advancing.

### Definition of “learned”

You have learned a topic only when you can:

- explain its purpose and failure modes without notes;
- implement a small version manually;
- test the important success and failure path; and
- identify when **not** to use it.

### Study rhythm

Use a gate-based rhythm rather than a deadline:

- **Learn:** one focused concept at a time.
- **Build:** one small exercise that proves it.
- **Review:** inspect the result, identify debt, record the next question.
- **Integrate:** only when the exercise has a direct place in the current product milestone.

Keep one `learning-log.md` or issue per exercise with: objective, source links, result, failure observed, and next improvement.

---

## 2. Capability map

| Product milestone | You must understand before coding it |
|---|---|
| M0 — local health proof | Python, virtual environments, Git, HTTP, config, logs, Docker, SQL basics |
| M1 — Provider identity/heartbeat | REST design, PostgreSQL schema/migrations, authentication, background loops, retries, state machines |
| M2 — media feasibility spike | Browser JavaScript/TypeScript, WebRTC, signaling, ICE/STUN/TURN, networking telemetry |
| M3 — safe internal session | Windows processes, subprocess supervision, least privilege, idempotent commands, lifecycle reconciliation |
| M4/M5 — authorized beta | threat modeling, privacy, incident response, title approval workflow, observability, support operations |
| M6 — payments | ledger design, webhook verification, idempotency, marketplace payouts, refunds/disputes |
| M7 — scale | deployment, CI/CD, monitoring, backups, load testing, SLOs, staged rollout |
| M8 — compute, optional | Linux, Docker internals, GPU containers, artifact storage, sandbox escape testing |

---

## 3. Phase A — Core builder workflow

### Learn

- Git: status, add, commit, branch, diff, pull, push, merge conflict resolution.
- Windows terminal basics: paths, environment variables, process exit codes, ports, virtual-environment activation.
- Python 3: modules, functions, classes, exceptions, context managers, type hints, dataclasses, `pathlib`, `logging`.
- Dependency management: virtual environments, pinned versions, lockfiles, why `.env` must not enter Git.
- Test fundamentals: arrange/act/assert, deterministic tests, boundary and failure cases.

### Build manually

1. Create a small Python command-line program that loads one required environment variable.
2. Make it return a non-zero exit code and a useful error when the variable is missing.
3. Add a test for success and missing configuration.
4. Commit the exercise with a meaningful commit message.

### You pass when

- You can create/recreate a virtual environment without help.
- You understand the difference between a tracked `.env.example` and an ignored real `.env`.
- You can read a traceback, find the first relevant application frame, and fix the cause.
- You can explain why a test should check behavior rather than implementation text.

### Official-first references

- [Python tutorial](https://docs.python.org/3/tutorial/)
- [Python `venv`](https://docs.python.org/3/library/venv.html)
- [Python logging](https://docs.python.org/3/library/logging.html)
- [pytest documentation](https://docs.pytest.org/)
- [Pro Git book](https://git-scm.com/book/en/v2)

---

## 4. Phase B — HTTP APIs and configuration

### Learn

- HTTP methods, request/response headers, JSON, status codes, timeouts, retries, and idempotency.
- REST resource design: nouns, request validation, error contract, pagination, and versioning boundaries.
- FastAPI: route handlers, Pydantic request/response models, dependency injection, exception handlers, OpenAPI output.
- Configuration hierarchy: defaults, environment variables, `.env` only for local development, secret injection in deployment.
- Structured logs: severity, event names, correlation IDs, and why logs must not contain credentials.

### Build manually

1. Build the M0 orchestrator `GET /health` endpoint.
2. Return one stable JSON contract for healthy and unhealthy database states.
3. Add `GET /version` with application version/commit metadata but no secrets.
4. Write API tests for valid response, missing database config, and unavailable database.
5. Call the endpoint using a browser and a command-line HTTP client.

### You pass when

- You can distinguish a `400`, `401`, `403`, `404`, `409`, `422`, `429`, and `500`.
- You can explain why a health endpoint must not leak credentials or internal stack traces.
- You can describe why retrying an unsafe request can duplicate work.

### References

- [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/)
- [MDN HTTP overview](https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview)
- [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110)

---

## 5. Phase C — PostgreSQL, data modeling, and migrations

### Learn

- SQL tables, primary/foreign keys, constraints, indexes, transactions, isolation, and query plans.
- PostgreSQL connection handling and why a connection pool is not a permanent connection.
- Database schema evolution: migrations are code, reviewed and reversible where possible.
- Data invariants: enforce critical facts in the database, not only in API validation.
- Repository/service boundary: database access should not leak throughout request handlers.

### Build manually

1. Run local PostgreSQL through Docker Compose.
2. Connect from the orchestrator and execute `SELECT 1` for M0.
3. Create a migration for a minimal `provider_nodes` table.
4. Add a unique node identity and check constraint for allowed status values.
5. Write one integration test that starts with an empty database and applies the migration.

### You pass when

- You can explain why “online” is time-bound observed state rather than a permanent boolean.
- You know when to use a transaction.
- You can add a migration without deleting/recreating all data.
- You can identify which columns need an index from an actual query pattern.

### References

- [PostgreSQL tutorial](https://www.postgresql.org/docs/current/tutorial.html)
- [PostgreSQL constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [Docker Compose overview](https://docs.docker.com/compose/)

---

## 6. Phase D — Distributed control-plane fundamentals

This is the most important backend learning phase. A remote Provider agent is a distributed system, even with one machine.

### Learn

- State machines and allowed transitions.
- Leases, TTLs, heartbeats, clock-skew tolerance, and observed versus desired state.
- Idempotency keys, optimistic concurrency/version checks, duplicate delivery, and at-least-once behavior.
- Background jobs, cancellation, timeouts, exponential backoff with jitter, and dead-letter/reconciliation concepts.
- Append-only audit events versus mutable current state.

### Build manually

1. Model `ProviderNode` states: `pending_approval → enrolled → online_idle → offline/revoked`.
2. Build `POST /providers/register` and `POST /providers/heartbeat`.
3. Give each heartbeat a timestamp, node ID, request ID, and expected node state/version.
4. Implement a TTL sweeper that marks stale nodes offline.
5. Send the same heartbeat twice and prove it does not create duplicate state or events.
6. Stop the agent abruptly and prove the node becomes stale/offline after its lease expires.

### You pass when

- You can explain why TCP success does not prove a remote process completed work.
- You can explain why retries require idempotency.
- You can draw the state transition diagram and name who is allowed to advance each transition.
- You can answer: “What happens if the API commits but the agent dies before its reply?”

### Reference concepts

- [Martin Kleppmann: Designing Data-Intensive Applications](https://dataintensive.net/) — distributed-systems concepts; read selectively.
- [PostgreSQL transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)

---

## 7. Phase E — Authentication, device identity, and security basics

### Learn

- Authentication versus authorization versus accounting.
- Password hashing, session tokens, JWT tradeoffs, refresh/expiry, revocation, and audience/issuer claims.
- Device enrollment: one-time enrollment token, local keypair, node identity, rotation, revocation.
- TLS, certificate validation, secrets management, least privilege, and why a client must not receive broad credentials.
- Threat modeling: assets, actors, entry points, trust boundaries, threats, mitigations, residual risk.

### Build manually

1. Make Provider enrollment a one-time, expiring, admin-approved operation.
2. Store only a credential verifier/public key or equivalent safe identity record—not a reusable enrollment secret.
3. Require the agent to authenticate every heartbeat.
4. Add node revocation and prove a revoked node cannot heartbeat or receive a session command.
5. Write the first threat model for the browser, orchestrator, agent, and media host boundary.

### You pass when

- You can explain why a user token and a device token should not have the same powers.
- You know the difference between authentication, permission checks, and audit logging.
- You can identify the blast radius of a stolen agent credential.
- You can state the residual risk of a dedicated host versus a personal PC.

### References

- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)
- [OWASP Threat Modeling](https://owasp.org/www-community/Threat_Modeling)
- [OWASP Software Supply Chain Security](https://cheatsheetseries.owasp.org/cheatsheets/Software_Supply_Chain_Security_Cheat_Sheet.html)

---

## 8. Phase F — Windows agent and host lifecycle

### Learn

- Windows process model: parent/child process trees, exit codes, working directories, environment inheritance, services versus foreground processes.
- Python `subprocess`, process supervision, graceful shutdown, timeouts, and cleanup.
- Hardware discovery: CPU/RAM, GPU/driver/encoder support, temperature/power telemetry; treat every reading as optional/versioned data.
- Windows users, UAC, file permissions, and least-privileged service accounts.
- Why capture policy and blocked keyboard chords reduce risk but do not securely isolate a personal desktop.

### Build manually

1. Write an agent that loads only its required config and pings M0 `/health`.
2. Add a periodic heartbeat with hardware snapshot stub data first, then real safe telemetry.
3. Create a process supervisor for one harmless test executable; allow only a fixed executable and fixed arguments.
4. Implement stop, timeout, crash detection, and cleanup confirmation.
5. Add a local emergency-stop command that always works when the orchestrator is unavailable.

### You pass when

- You can stop a child process tree without leaving an orphaned process.
- You can explain the difference between observed process status and requested process status.
- You can explain why the agent must never accept arbitrary shell command text from the API.

### References

- [Python `subprocess`](https://docs.python.org/3/library/subprocess.html)
- [Microsoft AppContainer isolation](https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation)
- [Windows Sandbox overview](https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-overview)

---

## 9. Phase G — Browser client and web application fundamentals

### Learn

- Modern JavaScript first, then TypeScript: modules, promises, `async`/`await`, browser events, DOM, fetch, errors, and cancellation.
- Browser security: same-origin policy, CORS, Content Security Policy, secure cookies versus bearer tokens, XSS basics.
- UI state: loading, retry, cancellation, error honesty, and explicit session lifecycle display.
- Input handling: focus, pointer lock, keyboard/gamepad events, accessibility, and the distinction between input capture and safe injection.

### Build manually

1. Create a minimal page that lists mock catalog entries from the API.
2. Add a “request session” flow with loading, success, cancellation, and no-capacity states.
3. Add a session status view driven by mocked state transitions.
4. Build an input event viewer locally; do not inject inputs into a remote host yet.
5. Add a simple network preflight measurement view.

### You pass when

- You can trace every user-visible state to an API/session state.
- You can explain CORS and why it is not authentication.
- You handle rejected/slow requests without a frozen UI or silent failure.

### References

- [MDN JavaScript guide](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide)
- [MDN Web security](https://developer.mozilla.org/en-US/docs/Web/Security)
- [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/intro.html)

---

## 10. Phase H — WebRTC and real-time networking

### Learn before coding

- SDP offer/answer, signaling, ICE candidates, STUN, TURN, NAT types, relay versus direct connection, RTP/RTCP, SRTP, codecs, and connection states.
- WebRTC does **not** provide your signaling/authentication/application state machine.
- TURN is bandwidth infrastructure and a privacy/product decision, not an optional last-minute fallback.
- Browser diagnostics: `getStats()`, selected candidate pair, packet loss, jitter, bitrate, and connection-state events.

### Build manually

1. Build a localhost browser-to-browser video/data-channel demo.
2. Replace manual SDP copy/paste with a tiny authenticated signaling service.
3. Add ICE candidate exchange and log every connection state transition.
4. Test on two networks using authenticated TURN credentials.
5. Record direct/relay outcome, setup duration, and failure reason.
6. Only then connect the selected media-host candidate.

### You pass when

- You can draw the signal path separately from the media path.
- You can explain why STUN cannot guarantee connectivity and TURN can relay media.
- You can diagnose whether a failure is signaling, ICE, codec, media-host, or browser input.

### References

- [WebRTC peer connections](https://webrtc.org/getting-started/peer-connections)
- [MDN WebRTC protocols](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API/Protocols)
- [MDN `RTCPeerConnection.getStats`](https://developer.mozilla.org/en-US/docs/Web/API/RTCPeerConnection/getStats)

---

## 11. Phase I — Media pipeline, capture, codecs, and input

### Learn

- Video capture, color formats, frame pacing, hardware encoders, bitrate/resolution/frame-rate tradeoffs, hardware decoder compatibility, audio capture, and A/V sync.
- H.264/AV1 capability negotiation at a conceptual level; do not write codec implementations.
- Windows capture choices and their privacy constraints.
- Existing media-host architecture, operational maturity, license obligations, release/update model, and browser-client compatibility.
- Input safety policy: allowlisted input events, session focus, chord filtering, rate limits, and local emergency termination.

### Build manually

1. Evaluate two media approaches in the M2 spike; do not build an encoder or WebRTC stack from scratch.
2. Stream a harmless test application or rights-cleared title from a dedicated host.
3. Instrument launch-to-first-frame, codec, bitrate, FPS, RTT, direct/relay path, and stream-host exit cause.
4. Demonstrate bounded input to the test application and prove blocked inputs cannot invoke arbitrary system actions.
5. Write ADR-003 choosing, rejecting, or postponing the media stack.

### You pass when

- You can explain the measured bottleneck: encode, upload, relay, decode, browser, or input.
- You can state the license and maintenance consequences of the chosen media component.
- You can terminate a session and prove cleanup/release occurs.

### References

- [Sunshine documentation](https://docs.lizardbyte.dev/projects/sunshine/latest/)
- [Sunshine license](https://github.com/LizardByte/Sunshine/blob/master/LICENSE)
- [WebRTC codec guide](https://webrtc.org/media/)

---

## 12. Phase J — Observability, testing, and operations

### Learn

- Structured logging, metrics, traces, correlation IDs, dashboards, alerts, and privacy-minimized telemetry.
- Unit, integration, end-to-end, contract, load, and failure-injection tests.
- Backups, restore testing, migration discipline, deployment environments, CI/CD, artifact signing, staged rollout, rollback.
- SLOs: define service quality as measurable success/error budgets, not feelings.

### Build manually

1. Attach a `session_id`, `node_id`, `command_id`, and `request_id` to every relevant event.
2. Build one dashboard/query showing session-state counts and failure categories.
3. Write an integration test: enroll agent → heartbeat → reserve → process crash → reconcile → release.
4. Restore a test database backup into a fresh local database.
5. Run a staged agent update against one test host and prove rollback.

### You pass when

- You can diagnose a failed session from evidence rather than guessing.
- You know whether a metric is a counter, gauge, histogram, or event.
- You have tested recovery, not only the happy path.

---

## 13. Phase K — Product, legal, support, and marketplace operations

These are founder skills, not code libraries. Learn them before commercial launch.

### Learn

- Title Approval Records, rights evidence, terms change monitoring, legal counsel handoff, and why store ownership does not establish commercial streaming permission.
- Provider onboarding, dedicated-host requirements, incident handling, acceptable-use policy, privacy disclosures, and support workflows.
- Marketplace liquidity, supply acquisition, consumer activation, cohort design, price experiments, contribution margin, refunds, and disputes.
- Payment mechanics: authorization, capture, ledger, webhooks, connected accounts, KYC, payout holds, chargebacks, tax obligations.

### Build manually

1. Create a Title Approval Record template and use it for a test application/authorized title.
2. Run five user interviews before expanding the catalog or writing payment code.
3. Define a Provider onboarding checklist for dedicated hardware.
4. Model one session ledger on paper/database: requested, authorized, live seconds, refund, Provider earning, platform fee, payout hold.
5. Simulate payment-provider webhooks and duplicate delivery before touching real money.

### You pass when

- You can calculate measured contribution margin for one completed session.
- You can explain why the platform must not move money based only on a client-reported duration.
- You have a written answer for “what happens when a session fails after a Consumer is charged?”

### References

- [Steam Subscriber Agreement](https://store.steampowered.com/subscriber_agreement/)
- [Stripe Connect](https://docs.stripe.com/connect)
- [OWASP Logging Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html)

---

## 14. Phase L — General compute, only after gaming gates

Do not study/build this now. Start only if the gaming path reaches its product/rights/safety gates and you deliberately choose the compute business.

### Learn later

- Linux administration, Docker internals, namespaces/cgroups, container networking, image supply chain, GPU pass-through, artifact storage, job scheduling, and sandbox escape testing.
- Compute is hostile-workload execution. It needs a new threat model; Docker alone is not a security promise.

### First future proof

A disposable test host runs an untrusted sample job with no host-home access, no undeclared mounts, constrained network/resource access, declared artifact output only, and verified cleanup.

---

## 15. Anti-roadmap — do not learn/build yet

Do **not** spend time on these before the preceding gates require them:

- Kubernetes, multi-region AWS, service mesh, microservices, Kafka, or custom distributed schedulers.
- Blockchain, tokens, crypto settlement, dynamic auction pricing, or provider reputation algorithms.
- A custom C++ WebRTC/capture/encoder engine.
- Native mobile apps, iOS/Android clients, or elaborate UI design system.
- Payments, public onboarding, anonymous Provider supply, or multi-title catalog growth.
- Dockerized untrusted compute.

They are not forbidden forever. They are dangerous distractions now.

---

## 16. Your next learning sequence

Do this next, in order:

1. **Finish M0 manually:** Git hygiene, `.env.example`, Docker Postgres, FastAPI health endpoint, DB health check, agent health ping.
2. **Make M0 testable:** tests for configuration/database failure plus one manual smoke test.
3. **Learn Phase D concepts:** state machines, idempotency, TTLs, retries, reconciliation.
4. **Build M1 manually:** approved Provider enrollment and heartbeats—no process launch yet.
5. **Start JavaScript/TypeScript and WebRTC fundamentals while M1 stabilizes.**
6. **Run M2 media feasibility spike.** Let its evidence choose browser/native path and host stack.

When you begin a phase, send this check-in for review:

```text
LEARNING PHASE:
CONCEPT I STUDIED:
WHAT I BUILT MANUALLY:
WHAT I EXPECTED:
WHAT ACTUALLY HAPPENED:
FAILURE / CONFUSION:
MY NEXT DESIGN DECISION:
```

---

## One-line rule

**Learn only the next layer needed to prove the product safely; convert every lesson into a small manual build and a measured gate.**
