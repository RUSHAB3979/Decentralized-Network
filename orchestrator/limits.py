"""Admission control: rate limits and concurrency ceilings.

WHY THIS IS A SEPARATE FILE. Every limit in here exists because some endpoint
does expensive work *before* it knows whether the caller deserves it. That is a
different problem from authentication, and putting it beside the handlers would
scatter five copies of the same bookkeeping through main.py.

Two shapes, because there are two kinds of expensive:

`RateLimiter` bounds how OFTEN one caller may ask. It is the answer to a
password endpoint: scrypt is deliberately slow and memory-hungry, so an
unauthenticated caller who can trigger it freely has been handed a lever with
enormous mechanical advantage -- a few dozen concurrent logins for addresses
that do not exist will saturate the CPU of the machine this marketplace runs
on. Rate limiting is the only defence that works before identity is known,
because the whole point of a login attempt is that the caller has not proved
anything yet.

`Gate` bounds how MANY may be in flight at once. It is the answer to a handler
that blocks -- /v1/chat/completions waits up to two minutes for a provider to
answer, holding a FastAPI threadpool worker and reopening a database connection
on every poll. Without a ceiling, enough concurrent requests starve every other
endpoint including /health, and the outage looks like a database problem rather
than a queue that was allowed to grow without bound.

REFUSAL IS THE FEATURE. Both classes reject rather than queue. A queue that
grows without limit converts a load spike into a slow, total outage with no
error anyone can act on; a 429 or a 503 with Retry-After is a fact the caller
can respond to. This is the same reasoning liveness.py applies to derived state:
prefer the answer that is visibly wrong over the one that is quietly wrong.

IN-PROCESS, AND THAT IS A STATED LIMIT. The counters live in this process's
memory. One orchestrator instance is the current deployment, so this is accurate
today; behind two instances each would enforce its own share and the effective
limit doubles. Moving to Redis is the fix, and it is not needed until there is a
second instance. It is written here rather than left implicit because the
failure mode -- a limit that silently means twice what it says -- is exactly the
kind that gets discovered during an incident.
"""

from __future__ import annotations

import os
import threading
import time
from collections import OrderedDict, deque

# A cap on how many distinct callers we track. Without it the limiter is itself
# an unbounded allocation: an attacker rotating source addresses (or forging
# X-Forwarded-For, which we do not trust for exactly this reason) would grow the
# dictionary until the process dies -- a memory exhaustion bug introduced by the
# code meant to prevent resource exhaustion. Least-recently-used entries are
# evicted, so a flood of one-shot keys pushes out other one-shot keys rather
# than the established callers who are actually being limited.
MAX_TRACKED_KEYS = 8192


class RateLimited(Exception):
    """Too many requests from this key inside the window.

    Carries `retry_after` in seconds so the handler can send a Retry-After
    header. A 429 without one tells a client to back off by an amount it has to
    guess, and clients that guess badly retry immediately.
    """

    def __init__(self, retry_after: float) -> None:
        super().__init__(f"rate limited; retry in {retry_after:.0f}s")
        self.retry_after = max(1, int(round(retry_after)))


class AtCapacity(Exception):
    """Every slot for this operation is already in use."""


class RateLimiter:
    """Sliding-window limiter: at most `limit` events per `window_s` per key.

    Sliding rather than fixed-window because a fixed window lets a caller spend
    its whole allowance at 0:59 and the next window's at 1:01 -- double the
    intended rate at the exact moment a limiter is supposed to be strictest.
    Keeping the timestamps costs `limit` floats per key, which is affordable
    precisely because `limit` is small.
    """

    def __init__(self, limit: int, window_s: float) -> None:
        self.limit = max(1, limit)
        self.window_s = max(1.0, float(window_s))
        self._events: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = threading.Lock()

    def check(self, key: str, now: float | None = None) -> None:
        """Record one event for `key`, or raise RateLimited.

        Deliberately not a two-step "allowed?" then "record it": between those
        two calls a second thread can pass the same check, which is how limiters
        end up permitting twice their limit under concurrency.
        """
        moment = time.monotonic() if now is None else now
        with self._lock:
            events = self._events.get(key)
            if events is None:
                events = deque()
                self._events[key] = events
            self._events.move_to_end(key)

            horizon = moment - self.window_s
            while events and events[0] <= horizon:
                events.popleft()

            if len(events) >= self.limit:
                # The oldest event in the window is what has to age out before
                # another is allowed, so that is the honest retry time.
                raise RateLimited(events[0] + self.window_s - moment)

            events.append(moment)

            while len(self._events) > MAX_TRACKED_KEYS:
                self._events.popitem(last=False)

    def reset(self) -> None:
        """Drop all state. For tests, so one case cannot exhaust another's budget."""
        with self._lock:
            self._events.clear()


class Gate:
    """A non-blocking concurrency ceiling.

    `acquire()` either takes a slot immediately or raises. It never waits --
    waiting for a slot on a handler that exists because the handler is slow just
    moves the queue somewhere the operator cannot see it.
    """

    def __init__(self, capacity: int) -> None:
        self.capacity = max(1, capacity)
        self._in_flight = 0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            if self._in_flight >= self.capacity:
                raise AtCapacity(
                    f"all {self.capacity} slots for this operation are in use"
                )
            self._in_flight += 1

    def release(self) -> None:
        with self._lock:
            # Clamped rather than allowed to go negative. A release without a
            # matching acquire is a bug in the caller, and letting the counter
            # drift below zero would hide it by silently raising the ceiling.
            self._in_flight = max(0, self._in_flight - 1)

    def __enter__(self) -> "Gate":
        self.acquire()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.release()

    @property
    def in_flight(self) -> int:
        with self._lock:
            return self._in_flight


def _int_env(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


# --------------------------------------------------------------------------
# The configured limiters. Module-level singletons because the state has to
# outlive a request; read from the environment once at import, unlike ttl() and
# friends in main.py, because a limiter whose window changes underneath its own
# recorded timestamps enforces neither the old limit nor the new one.
# --------------------------------------------------------------------------

# Password endpoints. Five attempts per address per minute is far above what a
# human typing a password needs and far below what an offline-grade guessing
# run or a CPU-exhaustion attempt requires.
AUTH_ATTEMPTS = _int_env("AUTH_RATE_LIMIT", 5)
AUTH_WINDOW_S = _int_env("AUTH_RATE_WINDOW_SEC", 60)

auth_by_address = RateLimiter(AUTH_ATTEMPTS, AUTH_WINDOW_S)

# A second limiter keyed on the account being targeted, not the caller. Without
# it, a distributed guessing run against one known address stays under the
# per-address limit while still trying thousands of passwords for that account.
auth_by_account = RateLimiter(
    _int_env("AUTH_ACCOUNT_RATE_LIMIT", 10),
    _int_env("AUTH_RATE_WINDOW_SEC", 60),
)

# How many password hashes may run at once. scrypt at n=2**14, r=8 needs roughly
# 16 MiB each, so this multiplied by 16 MiB is the memory this endpoint can
# commit -- on a 512 MB instance that arithmetic is the whole reason for the
# ceiling. Callers beyond it get 503, not a slow success.
password_hashing = Gate(_int_env("AUTH_HASH_CONCURRENCY", 4))

# Blocking inference requests in flight. FastAPI's default threadpool is 40
# workers; leaving headroom means a saturated inference queue cannot take
# /health, the console, or the render endpoints down with it.
inference_in_flight = Gate(_int_env("INFERENCE_CONCURRENCY", 12))

# Per-key ceiling inside the global one, so a single customer cannot occupy
# every slot and turn their own load into everybody's outage.
INFERENCE_PER_KEY = _int_env("INFERENCE_PER_KEY_CONCURRENCY", 4)

_per_key_lock = threading.Lock()
_per_key: OrderedDict[str, int] = OrderedDict()


class _PerKeySlot:
    def __init__(self, key: str) -> None:
        self.key = key

    def __enter__(self) -> "_PerKeySlot":
        with _per_key_lock:
            current = _per_key.get(self.key, 0)
            if current >= INFERENCE_PER_KEY:
                raise AtCapacity(
                    f"this API key already has {current} requests in flight; "
                    f"the limit is {INFERENCE_PER_KEY}"
                )
            _per_key[self.key] = current + 1
            _per_key.move_to_end(self.key)
        return self

    def __exit__(self, *_exc: object) -> None:
        with _per_key_lock:
            remaining = _per_key.get(self.key, 1) - 1
            if remaining <= 0:
                # Removed rather than left at zero, so an idle key costs no
                # memory and the map cannot grow without bound.
                _per_key.pop(self.key, None)
            else:
                _per_key[self.key] = remaining


def per_key_slot(key: str) -> _PerKeySlot:
    return _PerKeySlot(key)
