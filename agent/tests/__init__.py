"""Agent tests.

Nothing in this package may import agent.ui, agent.app, or anything that pulls
in pystray, pywebview or Pillow. CI installs ruff, pytest, httpx and
orchestrator/requirements.txt only (.github/workflows/ci.yml), so a test that
reaches the desktop layer fails on import and takes the whole suite with it.

The constraint is easy to satisfy because the agent is already split that way:
identity, telemetry and reporting are headless, and the GUI only reads them.
"""
