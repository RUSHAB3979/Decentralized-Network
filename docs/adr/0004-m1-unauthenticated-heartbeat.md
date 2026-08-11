# ADR 0004 — The M1 heartbeat endpoint is unauthenticated

Status: accepted for M1 only, with a named expiry condition
Date: 2026-08-11
Supersedes: nothing. Superseded by: whatever ships with `agent/core/creds.py`.

`docs/Tasks/tasks.md` M1 item 7 asks for a decision on whether an
unauthenticated heartbeat endpoint is acceptable for M1, and for the reasoning
to be written down rather than left implicit. This is that document.

## Decision

`POST /providers/register` and `POST /providers/heartbeat` accept any caller.
A `node_id` identifies the sender; nothing proves the sender is that node.

## What an attacker can actually do

Being precise about this matters more than the decision itself, because the
decision is only defensible if the list is short.

1. **Register nodes that do not exist.** Rows appear in `provider_nodes` with
   invented hostnames and GPUs. Cost: a polluted registry and a misleading
   count on the website.
2. **Impersonate a known node.** Guessing a `node_id` is hard — it is a
   truncated SHA-256 — but it is not secret, so anyone who has seen one can
   overwrite that node's metrics, or keep it looking online after it has gone.
3. **Deregister by omission.** An attacker cannot delete a node (there is no
   delete endpoint) but can make a live node appear busy or draining.
4. **Fill the table.** Unbounded registration is a storage and cost issue.

What an attacker **cannot** do, and this is the load-bearing part: obtain work,
obtain a customer prompt, obtain payment, or affect anyone's balance. None of
those exist in M1. There is no lease to claim, no meter to inflate, and no
payout to redirect. The asset behind this endpoint is a status row.

## Why not add authentication now

Because the honest options are all worse than waiting.

A shared secret compiled into the desktop build is not authentication. Every
provider gets the same string, it ships inside a PyInstaller bundle that anyone
can unpack, and its presence would let a reviewer believe the endpoint was
protected when it was not. That is strictly worse than no authentication: it
converts a known gap into an unknown one.

Per-node credentials are the correct answer, and they are exactly what
`agent/core/creds.py` is for. That module is hand-built under ADR 0002 —
credential handling is a component whose defects fail silently while appearing
to succeed — so it is Rushab's to write, and it is not written. Inventing a
scheme now to be replaced later means designing the enrolment handshake twice
and shipping the first attempt to real machines.

Guessing at a scheme also risks the thing ADR 0002 exists to prevent: generated
security code that looks right in review, passes its tests, and is wrong in a
way nothing raises about.

## The condition that ends this

This ADR expires the first time a `node_id` is attached to anything of value.
Concretely, **any of the following makes the current state unacceptable**:

- a lease can be claimed by node id (M2);
- usage is recorded against a node id (metering);
- a payout is computed from a node id (earnings);
- the node list becomes visible to customers as an availability signal they
  pay against.

The first of those is the next milestone. This is a short-lived exception, not
a standing position.

## What was done instead

The cost of the gap was reduced where it was cheap to do so:

- Every field is validated at the edge (`orchestrator/models.py`), and unknown
  fields are rejected, so a forged payload cannot smuggle values past the
  schema.
- `node_id` is constrained by pattern and length, so it cannot be used as an
  injection vector or to write unbounded keys.
- `local_models` is capped, so a forged heartbeat cannot store an unbounded
  list.
- Heartbeat is an `UPDATE`, not an upsert: a caller cannot create nodes through
  the heartbeat endpoint, only through registration.
- Nothing on the provider path can read customer data. There is no such data
  in the orchestrator yet, and `agent/requirements.txt` has no database driver,
  so a compromised agent has no reach beyond these two endpoints.

Rate limiting is **not** in place. It is the obvious next mitigation and it is
worth doing before the endpoint is exposed outside localhost, independently of
credentials.

## Deployment constraint

While this ADR stands, the orchestrator must not be exposed to the public
internet. M1 runs on localhost and on a trusted LAN. That constraint is part of
the decision, not a separate operational detail: the reasoning above assumes the
set of people who can reach the endpoint is small and known.
