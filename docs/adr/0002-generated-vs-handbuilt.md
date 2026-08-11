# ADR 0002 — What we generate and what we hand-build

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-11 |
| **Owner** | [@RUSHAB3979](https://github.com/RUSHAB3979) (R1 Architect) |
| **Supersedes** | The M0 rule that the founder writes every line of `orchestrator/` and `agent/` |

---

## Context

M0 was built under a deliberate rule: the founder hand-wrote every line of
`orchestrator/` and `agent/` as a learning exercise, and the agent contributed
planning, review and failure-case design but no implementations.

That rule produced real value — see the Block C and D findings in
`docs/Tasks/tasks.md`. It also cost 26 days at roughly two to three hours a day
to reach a milestone whose definition of done is "Postgres is up, `/health`
returns OK, the agent pings it." College placement preparation takes priority
over this project and will continue to. Extrapolated across the remaining
lanes in `docs/Plans/plan.md` §2.1, hand-writing everything does not finish.

The opposite extreme fails differently. Generating the whole system produces a
codebase whose hardest component cannot be debugged by the only person who
would have to debug it.

## Decision

**Generate by default. Hand-build the code that fails silently.**

The line is drawn by failure mode, not by directory or language.

Code that **throws** when it breaks is generated. A stack trace names the file
and the line, the defect is visible on the first run, and nothing is lost by
not having typed it.

Code that **degrades** when it breaks is hand-built. Nothing raises. The system
keeps serving, the session is merely bad, and there is no error to search for.
You cannot debug what you did not build when the symptom is a number being
worse than it should be.

### Hand-built

| Area | Why it degrades instead of throwing |
|---|---|
| WebRTC negotiation, ICE candidate selection | A wrong candidate still connects — over relay, at triple the cost |
| TURN fallback and the decision to use it | Relay works. It just costs money and adds latency, silently |
| Capture → encode → transport pipeline | Produces video the whole way down while producing *bad* video |
| Anything with a timeout, retry or deadline | Block C/D: a 5s client timeout hid a 10s `503`, so the branch built to handle it had never once executed |
| Session lifecycle and teardown | A leaked session holds a GPU. Nothing reports this |
| Agent capability and reachability boundaries | `agent/requirements.txt` is a security boundary; shipping a DB driver there implies reach the agent must never have |

### Generated

| Area | Why generation is safe |
|---|---|
| `web-client/` in full | Already the practice. Failures are visible in a browser |
| CRUD endpoints, Pydantic models | Validation errors raise with the field name in them |
| Schema and migrations | Migrations fail loudly and roll back |
| Auth | Wrong is wrong: you are in or you are out |
| Billing and payments integration | The provider's API rejects malformed calls |
| CI, Docker, infrastructure config | A broken pipeline is red |
| Documentation, ADR scaffolding | Reviewed by reading, which is the only check it needs |

### The rule for anything not listed

Ask: *if this is wrong, will something raise?* If yes, generate it. If the
answer is "it will work, just worse," hand-build it.

## Sequencing

The boundary above does not by itself decide what to build next, and building
the right thing matters more than how it gets typed.

Every stop-or-pivot criterion in `plan.md` §1.4 is a question about the world,
not about code: whether a rights-cleared title exists, whether the media stack
meets quality on representative networks, whether relay stays under 20%,
whether provider supply stays online. None is answered faster by producing code
faster. Meanwhile the repository holds 4,299 lines of marketplace UI — Lane 3,
the lane that requires "legal, trust, economics, operations all proven" — and a
backend that has not yet reached Lane 1.

**Phase 0 — the measurement. Hand-built. Do this before anything else.**

Per the launch constraint in §1.3, do not write a media stack. Run a proven
one: a self-hosted host/client pair such as Sunshine with Moonlight is the
cheapest way to get a real session onto a real network. Stream one session the
project is legally permitted to stream — a test application or an open-licensed
title, not a commercial one — to one machine that is not on the same LAN.

Record: glass-to-glass latency at p95, the share of attempts that required
relay, and bitrate stability under loss. Those three numbers answer three of
the five stop criteria directly.

The media stack here is adopted, not written. What is hand-built is the
measurement: the harness that induces loss and the assertions about what
counts as acceptable. A generated harness that measures the wrong thing
reports success, which is the failure this ADR exists to prevent.

**Phase 1 — control plane. Generated.** M1's register and heartbeat endpoints,
the `ProviderNode` table, the Pydantic models. This is CRUD. It throws when it
is wrong. It only earns its place once Phase 0 says there is something to
orchestrate.

**Phase 2 — marketplace surface. Generated.** Already largely built. It stays
on mock data until Phase 0 and Phase 1 give it something real to display.

## Consequences

The founder ends up understanding a shrinking fraction of the codebase, and
that is accepted deliberately. The bet is that the fraction retained is the
fraction that matters at 2am.

Generated code still has to be read before it merges. The two worst incidents
in this repository — a 26-hour broken typecheck and a Tailwind major that took
`main` red for two and a half hours — were both caused by merging code nobody
read, not by generating it. This ADR increases the volume of code arriving
unread by default, so the review discipline in CI matters more now, not less.

The learning goal of M0 is retired. It succeeded: the four Block C and D
findings are the return on it, and they are what made the boundary above
choosable rather than arbitrary.

If Phase 0 fails its gate, most of Phase 1 and Phase 2 never get written, which
is the point of sequencing it first.

## Alternatives considered

**Keep hand-writing everything.** Rejected on arithmetic, not principle. M0 was
hello-world and took 26 days at the available cadence.

**Generate everything including the media path.** Rejected because the media
path is the product; the rest is a website around it, and its defects do not
surface as exceptions.

**Draw the line at directories — `orchestrator/` by hand, everything else
generated.** Rejected because it splits in the wrong place. Most of
`orchestrator/` will be CRUD, and the streaming work will not live there.
