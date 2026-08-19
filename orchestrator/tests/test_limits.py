"""Admission control: what it refuses, and what it must not refuse.

These run with no database and no server. Every case drives the limiter's own
clock through the `now` parameter rather than sleeping, so the sliding window is
tested at exact boundaries and the suite stays fast -- a rate-limit test that
sleeps through its own window is how a one-minute window becomes a one-minute
test run.

The concurrency cases matter more than they look. A limiter that permits twice
its limit under load is not a limiter, and that failure only appears when two
callers pass the same check before either records anything -- which never
happens in a single-threaded test.
"""

from __future__ import annotations

import threading

import pytest

from orchestrator import limits


def test_the_limit_is_a_ceiling_not_a_target():
    limiter = limits.RateLimiter(limit=3, window_s=60)
    for i in range(3):
        limiter.check("caller", now=1000.0 + i)

    with pytest.raises(limits.RateLimited):
        limiter.check("caller", now=1003.0)


def test_the_window_slides_rather_than_resetting():
    """A fixed window is the classic way to accidentally allow double the rate.

    With one, a caller spends its whole allowance at 0:59 and the next
    window's at 1:01 -- twice the intended rate at the exact moment the limiter
    is supposed to be strictest. Here the third attempt is refused while the
    first is still inside the window, and allowed the instant it ages out.
    """
    limiter = limits.RateLimiter(limit=2, window_s=60)
    limiter.check("caller", now=1000.0)
    limiter.check("caller", now=1030.0)

    with pytest.raises(limits.RateLimited):
        limiter.check("caller", now=1059.0)

    # 1000 + 60 = 1060, so the first event has left the window.
    limiter.check("caller", now=1061.0)


def test_retry_after_is_the_truth_and_never_zero():
    """A 429 whose Retry-After is a guess produces clients that retry instantly.

    The honest answer is when the oldest event in the window ages out, because
    that is exactly when another one is permitted. It is also rounded up to at
    least a second: a Retry-After of 0 is an invitation to hammer.
    """
    limiter = limits.RateLimiter(limit=1, window_s=60)
    limiter.check("caller", now=1000.0)

    with pytest.raises(limits.RateLimited) as raised:
        limiter.check("caller", now=1015.0)
    assert raised.value.retry_after == 45

    with pytest.raises(limits.RateLimited) as raised:
        limiter.check("caller", now=1059.99)
    assert raised.value.retry_after >= 1


def test_one_caller_being_limited_does_not_limit_anybody_else():
    # The failure this guards against is a shared counter: one abusive address
    # locking out every legitimate customer, which converts a small attack into
    # a total outage.
    limiter = limits.RateLimiter(limit=1, window_s=60)
    limiter.check("noisy", now=1000.0)
    with pytest.raises(limits.RateLimited):
        limiter.check("noisy", now=1000.0)

    limiter.check("quiet", now=1000.0)


def test_tracking_is_bounded_so_the_limiter_is_not_its_own_exhaustion_bug():
    """An attacker rotating keys must not be able to grow this map forever.

    Without the cap, the code written to prevent resource exhaustion is itself
    an unbounded allocation. Eviction is least-recently-used, so a flood of
    one-shot keys pushes out other one-shot keys rather than the established
    callers actually being limited.
    """
    limiter = limits.RateLimiter(limit=5, window_s=60)
    for i in range(limits.MAX_TRACKED_KEYS + 500):
        limiter.check(f"key-{i}", now=1000.0)

    assert len(limiter._events) <= limits.MAX_TRACKED_KEYS


def test_concurrent_callers_cannot_slip_past_the_limit_together():
    """The check and the record have to be one step.

    Split into "allowed?" then "record it", two threads can both pass before
    either records, and the limiter permits twice its limit under exactly the
    load it exists for. Sequential tests never see this.
    """
    limiter = limits.RateLimiter(limit=10, window_s=60)
    allowed = []
    start = threading.Barrier(20)

    def attempt():
        start.wait()
        try:
            limiter.check("shared", now=1000.0)
            allowed.append(1)
        except limits.RateLimited:
            pass

    threads = [threading.Thread(target=attempt) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(allowed) == 10


def test_reset_clears_every_key():
    limiter = limits.RateLimiter(limit=1, window_s=60)
    limiter.check("caller", now=1000.0)
    limiter.reset()
    limiter.check("caller", now=1000.0)


# -- Gate -------------------------------------------------------------------


def test_a_full_gate_refuses_instead_of_waiting():
    """Waiting is the wrong answer for a handler that exists because it is slow.

    A queue in front of /v1/chat/completions is invisible to the operator and
    turns a load spike into a slow total outage. Refusing produces a 503 the
    caller can act on.
    """
    gate = limits.Gate(capacity=2)
    gate.acquire()
    gate.acquire()

    with pytest.raises(limits.AtCapacity):
        gate.acquire()

    gate.release()
    gate.acquire()


def test_the_slot_is_returned_even_when_the_work_raises():
    """Otherwise every failed request permanently shrinks the ceiling.

    Capacity would decay towards zero over an incident -- the service getting
    quieter the more errors it saw, recovering only on restart.
    """
    gate = limits.Gate(capacity=1)
    with pytest.raises(ValueError):
        with gate:
            raise ValueError("the handler failed")

    assert gate.in_flight == 0
    gate.acquire()


def test_an_unmatched_release_cannot_raise_the_ceiling():
    # Letting the counter go negative would hide the caller's bug by silently
    # granting extra capacity -- the most expensive way to be wrong here.
    gate = limits.Gate(capacity=1)
    gate.release()
    gate.release()
    assert gate.in_flight == 0

    gate.acquire()
    with pytest.raises(limits.AtCapacity):
        gate.acquire()


def test_concurrent_acquires_never_exceed_capacity():
    gate = limits.Gate(capacity=5)
    taken = []
    start = threading.Barrier(20)

    def attempt():
        start.wait()
        try:
            gate.acquire()
            taken.append(1)
        except limits.AtCapacity:
            pass

    threads = [threading.Thread(target=attempt) for _ in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(taken) == 5
    assert gate.in_flight == 5


# -- per-key slots ----------------------------------------------------------


def test_one_key_cannot_occupy_more_than_its_share():
    """The point of the second, inner ceiling.

    With only a global limit, the first customer to fill it has denied service
    to every other customer while staying entirely within their rights.
    """
    key = "key-under-test"
    held = []
    try:
        for _ in range(limits.INFERENCE_PER_KEY):
            slot = limits.per_key_slot(key)
            slot.__enter__()
            held.append(slot)

        with pytest.raises(limits.AtCapacity):
            with limits.per_key_slot(key):
                pass

        # A different customer is unaffected, which is the whole purpose.
        with limits.per_key_slot("another-key"):
            pass
    finally:
        for slot in held:
            slot.__exit__()


def test_an_idle_key_is_forgotten_so_the_map_stays_bounded():
    # Left at zero instead of removed, every API key that ever made a request
    # would stay in memory for the life of the process.
    key = "briefly-busy"
    with limits.per_key_slot(key):
        assert limits._per_key[key] == 1
    assert key not in limits._per_key
