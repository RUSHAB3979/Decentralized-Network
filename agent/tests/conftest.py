"""Shared fixtures for the agent suite."""

from __future__ import annotations

import pytest

from agent import identity
from agent.runtime import blender


@pytest.fixture(autouse=True)
def _forget_blender_probe():
    """Stop one test's idea of this machine from becoming every test's.

    blender.installation() caches for the life of the process, deliberately --
    the reporter heartbeats every fifteen seconds and must not start a process
    each time. Under pytest that same cache means the first test to build a
    Worker fixes the answer for the rest of the run, so a test that patches
    find_binary() to simulate a machine without Blender would silently keep
    whatever the previous test installed. Clearing it on both sides of every
    test makes each one describe the machine it says it describes.
    """
    blender.forget_installation()
    yield
    blender.forget_installation()


@pytest.fixture(autouse=True)
def _forget_cached_source():
    """Stop one test's scene file from being served to the next.

    The source cache is module state keyed by job id, so a test that renders
    job "a" leaves a real file behind that a later test using the same id would
    silently reuse -- and pass without ever exercising the download it meant to
    test. Clearing on both sides also means the suite does not leave temporary
    scene files on the machine that ran it.
    """
    blender.forget_source_cache()
    yield
    blender.forget_source_cache()


@pytest.fixture(autouse=True)
def _stored_node_token(monkeypatch):
    """Every test runs as a node that holds a credential.

    The heartbeat is authenticated, so without this the suite's answer depends
    on whether the machine running it happens to have a registered agent's
    token in %LOCALAPPDATA%. That is not a hypothetical: this fixture lived in
    test_reporter.py, where autouse only reaches that one module, and
    test_link_state.py passed on a developer machine with a real token on disk
    and failed in CI, which has none. Suite-wide is the only scope that makes
    the answer describe the code rather than the machine.

    Tests about the absent-credential path opt out by patching it back to None.
    """
    monkeypatch.setattr(identity, "node_token", lambda: "test-node-token")
    monkeypatch.setattr(identity, "clear_node_token", lambda: None)
