"""Machine identity and the orchestrator credential. HAND-BUILT - see README.md.

Failure mode: a credential stored badly works exactly as well as one stored
well. There is no test that goes red, no traceback, and no moment where the
provider finds out. That is why this is not generated.

This file is a specification, not an implementation. Everything below is the
result of building M1 around the hole this module leaves; it is written down so
that whoever fills the hole is not rediscovering it.

--------------------------------------------------------------------------
WHAT M1 SETTLED, AND WHAT IT LEFT TO THIS MODULE
--------------------------------------------------------------------------

M1 shipped `agent/identity.py`, which produces a stable `node_id`. That is a
*public identifier*, not a credential: it is derived from the Windows MachineGuid
and is expected to appear in logs, URLs, support tickets, and the marketplace UI.
Anyone who learns it can already impersonate the node today, because
`POST /providers/heartbeat` is unauthenticated (see
`docs/adr/0004-m1-unauthenticated-heartbeat.md`).

So the split is:

    identity.py  ->  WHO this machine claims to be   (public, derivable)
    creds.py     ->  PROOF that the claim is true    (secret, unforgeable)

Do not let the existence of `identity.py` make this module look optional. ADR
0004 is explicitly a temporary position, and **this module is what retires it.**
The ADR lists the conditions that end it; the earliest of them is a lease
becoming claimable by node id.

--------------------------------------------------------------------------
DESIGN NOTES THAT ARE ALREADY DECIDED
--------------------------------------------------------------------------

- The credential belongs to the *machine*, not the person. A provider with two
  PCs has two of these, and revoking one must not log out the other.
- On Windows the storage answer is almost certainly DPAPI
  (`CryptProtectData`, user scope), not a file in %APPDATA% and not the
  registry. DPAPI ties the ciphertext to the Windows account, so copying the
  file to another machine yields nothing.
- Rotation has to work while the node is running, because the alternative is
  telling providers to reinstall.
- A customer's token must never appear here or anywhere else on this machine.
  It terminates at the gateway. This module handles the provider's own
  credential only.

--------------------------------------------------------------------------
DESIGN QUESTIONS M1 RAISED AND DID NOT ANSWER
--------------------------------------------------------------------------

1. **How does an unenrolled machine get its first credential?**
   Two shapes, both defensible, with different failure modes:

   (a) *Enrolment code.* The provider copies a short-lived code out of the web
       console and pastes it into the desktop app; the agent trades it for a
       long-lived credential. Binds the node to a human account, which is what
       payouts will eventually require. Costs a UI flow the app does not have.

   (b) *Trust on first registration.* The first `POST /providers/register` for
       an unseen node_id returns a secret. Zero friction, and wrong: a node_id
       is derivable from a machine the attacker does not have to own, and the
       first caller wins. Only acceptable if registration is itself gated.

   Whichever is chosen, write down what happens when the same machine enrols
   twice, because reinstalling Windows regenerates the MachineGuid and
   therefore the node_id, while restoring an image does not.

2. **What does the credential prove, and to which request?**
   The reporter sends `node_id` in the request *body*. If the credential is
   checked but not bound to that body field, any enrolled node can heartbeat as
   any other node, and the check buys nothing. The server must reject a request
   whose credential does not match the claimed node_id. State that as an
   invariant before writing the client half.

3. **How does a node recover when the registry has lost it?**
   Today `POST /providers/heartbeat` returns 404 for an unknown node and the
   agent silently re-registers (`agent/reporter.py`), so a wiped database
   self-heals. Once registration needs a credential, that path must still work
   for a machine that holds a valid credential but has no row - otherwise a
   restore-from-backup bricks every provider at once, quietly, and they will
   not all reinstall.

4. **What happens when `load()` returns None mid-run?**
   The reporter must not degrade to unauthenticated requests when the
   credential cannot be read: that is a downgrade attack in the shape of a
   convenience. It should move the node to ERROR and say so in the UI. This is
   the single most likely way for this module to fail *silently* in service,
   as opposed to at enrolment.

5. **Cost per call.** `Reporter.heartbeat()` runs every ~15s for the life of the
   process. If `load()` reaches DPAPI on every call, that is a syscall per
   heartbeat forever. Cache in memory, and make `clear()` and rotation
   invalidate the cache - a stale cached credential survives a revocation,
   which is precisely the failure this module exists to prevent.

6. **Clean deregistration on quit.** `agent/app.py::on_quit` currently cannot
   tell the orchestrator it is going away, because an unauthenticated shutdown
   endpoint would let anyone take any node offline. With a credential it
   becomes possible, and liveness stops depending on a 120s TTL for the common
   case of a provider quitting deliberately.

--------------------------------------------------------------------------
ACCEPTANCE, WHEN THIS IS EVENTUALLY WRITTEN
--------------------------------------------------------------------------

The tests that matter are the ones that fail loudly for a defect that would
otherwise be invisible:

- A credential written by one Windows account is unreadable by another on the
  same machine. (If this passes trivially, DPAPI is not actually being used.)
- `clear()` leaves nothing recoverable, and a subsequent `load()` returns None
  rather than a stale cached value.
- Rotation mid-run: the next request after `store()` uses the new credential,
  with no restart.
- A heartbeat signed for node A is rejected when it claims node B.
- The credential never appears in a log line, a traceback, or the dashboard.
"""

from __future__ import annotations


def load() -> str | None:
    """Return this machine's orchestrator credential, or None if unenrolled.

    Callers must treat None as "stop and report ERROR", never as "send the
    request without one". See design question 4.
    """
    raise NotImplementedError


def store(credential: str) -> None:
    """Persist the credential so it survives reboot but not exfiltration.

    Must be safe to call while the node is running: this is also the rotation
    path, and any in-memory cache has to be invalidated here.
    """
    raise NotImplementedError


def clear() -> None:
    """Remove the credential. Must leave the machine safely unenrolled."""
    raise NotImplementedError
