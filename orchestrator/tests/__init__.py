"""Orchestrator tests.

This file is not empty by accident. pytest walks upwards from a test module for
as long as it keeps finding `__init__.py`, and uses the first directory without
one as the import root. With this file and orchestrator/__init__.py present,
that root is the repository root, so `import orchestrator.models` resolves the
same way in CI as it does under uvicorn. Delete it and the imports break in a
way that looks like a missing dependency.
"""
