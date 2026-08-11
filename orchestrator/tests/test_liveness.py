"""Boundary tests for the one fact the marketplace is built on.

These run without a database, a network, or a real clock, because CI has none
of them -- .github/workflows/ci.yml installs orchestrator/requirements.txt and
nothing else, and there is no Postgres service container. A staleness test that
needs a live database is a test that never runs.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from orchestrator.liveness import DEFAULT_TTL, liveness

TTL = timedelta(seconds=120)
NOW = datetime(2026, 8, 11, 12, 0, 0, tzinfo=timezone.utc)


def test_never_heartbeated_is_distinct_from_offline():
    # A node that registered and never checked in is a broken agent install,
    # not a sleeping machine. Collapsing the two loses the only signal that
    # tells them apart.
    assert liveness(None, NOW, TTL) == "never_seen"


def test_recent_heartbeat_is_online():
    assert liveness(NOW - timedelta(seconds=5), NOW, TTL) == "online"


def test_exactly_at_the_ttl_is_still_online():
    # The boundary is inclusive. Stated as a test because an off-by-one here
    # would drop nodes exactly one heartbeat early, which looks like flaky
    # networking rather than like a bug in this function.
    assert liveness(NOW - TTL, NOW, TTL) == "online"


def test_one_second_past_the_ttl_is_offline():
    assert liveness(NOW - TTL - timedelta(seconds=1), NOW, TTL) == "offline"


def test_long_dead_node_is_offline():
    assert liveness(NOW - timedelta(days=30), NOW, TTL) == "offline"


def test_future_timestamp_is_treated_as_online():
    # Clock skew on a consumer desktop is common and is not the provider's
    # fault. This is only safe while heartbeat timestamps do not affect money.
    assert liveness(NOW + timedelta(minutes=5), NOW, TTL) == "online"


def test_default_ttl_matches_the_documented_env_default():
    # PROVIDER_TTL_MS=120000 in .env.example. If someone changes one without
    # the other, agents and orchestrator disagree about who is online.
    assert DEFAULT_TTL == timedelta(milliseconds=120000)
