"""Shared fixtures for the agent suite."""

from __future__ import annotations

import pytest

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
