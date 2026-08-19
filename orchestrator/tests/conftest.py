"""Shared fixtures for the orchestrator suite."""

from __future__ import annotations

import pytest

from orchestrator import limits


@pytest.fixture(autouse=True)
def _fresh_admission_control():
    """Give every test the whole rate-limit budget.

    The limiters are module-level singletons, because their state has to outlive
    a request. Under pytest that means one test's attempts are charged against
    the next one's allowance: the suite drives every request from the same
    client address, so a handful of tests that each post to /v1/auth/signup add
    up to a 429 in whichever test happens to run sixth. That failure moves when
    tests are added, reordered, or run with -k, which is the worst kind of
    flake to chase.

    Clearing on both sides also means a test that deliberately exhausts a limit
    cannot leave it exhausted for everything after it.
    """
    limits.auth_by_address.reset()
    limits.auth_by_account.reset()
    yield
    limits.auth_by_address.reset()
    limits.auth_by_account.reset()
