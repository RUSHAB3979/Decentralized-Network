"""Claiming, holding, draining and releasing work. HAND-BUILT - see README.md.

Failure mode: every bug in this file leaves a working system. A lease that is
not released still expires. A drain that does not finish still ends when the
process dies. Nothing raises; the number that moves is revenue, weeks later.

This is also the file ADR 0002 describes most directly - it carries deadlines,
retries and session teardown, all three of the categories that degrade rather
than throw. Block C in docs/Tasks/tasks.md is the worked example: a client
timeout shorter than the server's worst case meant the error branch built to
handle a 503 had never once executed.

Design notes worth settling before writing a line:

- Drain is not stop. Drain refuses new work and lets current work finish. A
  provider hitting it because they want to play a game will wait a few seconds;
  they will not wait for a queue.
- The lease needs a deadline the *orchestrator* enforces, because the failure
  this protects against is this machine disappearing. A lease whose expiry is
  tracked only here expires only if this code is running.
- Renewal has to be cheaper than reclaiming. Whatever heartbeat interval is
  chosen, write down the worst case it tolerates - and make sure the client
  timeout is longer than the server's slowest honest response, not shorter.
- Crash and unclean shutdown are the normal case, not the exception. Machines
  get put to sleep mid-job.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Lease:
    """One unit of claimed work."""

    lease_id: str
    model: str
    expires_at: float  # epoch seconds, per the orchestrator's clock


def claim(model: str) -> Lease | None:
    """Ask for work. None means none available, which is normal, not an error."""
    raise NotImplementedError


def renew(lease: Lease) -> Lease:
    """Extend a lease before it expires."""
    raise NotImplementedError


def release(lease: Lease) -> None:
    """Hand work back. Must be safe to call twice and safe to call after expiry."""
    raise NotImplementedError
