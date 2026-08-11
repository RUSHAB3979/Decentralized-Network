# ADR 0001 — Python now, C++ later

| Field | Value |
|---|---|
| **Status** | Draft |
| **Date** | 2026-08-11 |
| **Owner** | [@RUSHAB3979](https://github.com/RUSHAB3979) (R1 Architect) |
| **Task** | E2 |

---

## Context

*Facts from the repository, not judgements. Correct anything wrong here.*

- The control plane is Python — FastAPI, `orchestrator/` and `agent/`, decided
  2026-08-09 and migrated from a TypeScript implementation that still sits in
  `services/` as a frozen read-only contract reference.
- `docs/Plans/plan.md` §1.3 already records a launch constraint on media:
  *"Reuse/evaluate proven components; do not begin a greenfield C++ media
  stack."*
- `docs/Plans/manual-builder-learning-plan.md` §15 lists *"a custom C++
  WebRTC/capture/encoder engine"* on the anti-roadmap, with the qualifier that
  anti-roadmap items *"are not forbidden forever. They are dangerous
  distractions now."*
- No C++ exists in the repository today.

## The question this ADR has to settle

The two documents above do not say the same thing, and the difference matters.

- *"C++ later"* says the rewrite is deferred — it is coming, and the only open
  question is when.
- *"Reuse proven components"* says the rewrite may never happen — you would
  adopt an existing engine instead of writing one.

An ADR that leaves this ambiguous will be read as whichever the reader already
believed. Pick one.

## Decision

<!--
  One sentence. What is the position?
-->

## Trigger — what would have to become true

<!--
  The sentence that keeps this ADR from rotting.

  "Later" with no trigger means the rewrite happens on vibes, or never, and
  either way nobody can tell which. State the condition that would move the
  decision — ideally something measurable enough that you could be shown to be
  wrong about it.
-->

## Consequences

<!--
  What this costs you. Including the case where the trigger never fires.
-->

## Alternatives considered

<!--
  Only the ones you actually weighed. An alternative nobody considered is
  padding, not a record.
-->
