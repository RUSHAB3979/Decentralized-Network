"""Deciding whether a provider node is still there.

This is one small pure function in its own module for a reason. Whether a node
counts as online is the fact the whole marketplace is built on -- scheduling
will not send work to an offline node, and the website will not show one -- and
it is exactly the kind of fact that can be wrong without anything raising.

Two properties keep it honest.

It is *derived, never stored*. The alternative is a background task that marks
rows offline on a timer. That task can die, and when it does every row keeps
whatever flag it last had; the system reports a fleet of healthy nodes that are
all gone, and no exception is thrown anywhere. Deriving from a timestamp at read
time has no such failure mode: if no heartbeat arrives, the derived answer
changes on its own.

It is *pure*, so its behaviour at the boundaries can be tested without a
database, a clock, or a network -- which matters because CI has none of them.
"""

from __future__ import annotations

from datetime import datetime, timedelta

# Matches PROVIDER_TTL_MS in .env.example (120000). Roughly eight missed
# heartbeats at HEARTBEAT_SEC=15, which is deliberately forgiving: a provider
# on home Wi-Fi should survive a brief blip without being dropped from the
# marketplace and having to pay a model cold start to come back.
DEFAULT_TTL = timedelta(seconds=120)


def liveness(
    last_heartbeat_at: datetime | None,
    now: datetime,
    ttl: timedelta = DEFAULT_TTL,
) -> str:
    """Classify a node as 'online', 'offline', or 'never_seen'.

    'never_seen' is kept distinct from 'offline' on purpose. A node that
    registered and never heartbeated is a broken install -- the agent started,
    reached the orchestrator once, and then its heartbeat loop failed. A node
    that heartbeated and stopped is a machine that went to sleep. Collapsing
    them into one state throws away the only signal that tells the two apart.

    A heartbeat timestamped in the future is treated as online rather than
    rejected: clock skew on a consumer desktop is common and is not the
    provider's fault, and refusing it would drop honest nodes. This is safe
    only while heartbeats are unmetered; the moment a timestamp affects
    payment, skew becomes an attack and this has to be revisited.
    """
    if last_heartbeat_at is None:
        return "never_seen"
    return "online" if now - last_heartbeat_at <= ttl else "offline"
