"""Credential helpers for the inference gateway.

The local-runner test that used to live here moved to agent/tests/test_worker.py
when execution moved to the provider. The property it protected -- a customer's
API key never reaching the model runtime -- is now stronger than a test: the
process that talks to Ollama never receives the key at all.
"""

from __future__ import annotations

import pytest

from orchestrator import inference


def test_api_key_plaintext_is_not_its_stored_value():
    issued = inference.issue_api_key()

    assert issued.secret.startswith(inference.API_KEY_MARKER)
    assert issued.prefix == issued.secret[: inference.API_KEY_PREFIX_LENGTH]
    assert issued.digest == inference.hash_api_key(issued.secret)
    assert issued.secret not in issued.digest


def test_api_keys_are_unique():
    assert inference.issue_api_key().secret != inference.issue_api_key().secret


@pytest.mark.parametrize(
    "header",
    [None, "", "Basic abc", "Bearer", "Token abc"],
)
def test_invalid_authorization_headers_are_rejected(header):
    with pytest.raises(ValueError):
        inference.bearer_token(header)
