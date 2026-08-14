from __future__ import annotations

import json

import httpx
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


def test_chat_forwards_work_but_not_the_customer_key(monkeypatch):
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "message": {"role": "assistant", "content": "hello back"},
                "done": True,
                "prompt_eval_count": 4,
                "eval_count": 2,
                "total_duration": 1_500_000_000,
            },
        )

    monkeypatch.setenv("LOCAL_OLLAMA_URL", "http://ollama.invalid")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = inference.run_chat(
            model="tinyllama:latest",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.2,
            max_tokens=32,
            client=client,
        )

    assert "authorization" not in captured["headers"]
    assert captured["body"]["model"] == "tinyllama:latest"
    assert captured["body"]["stream"] is False
    assert result.content == "hello back"
    assert result.prompt_tokens == 4
    assert result.completion_tokens == 2
    assert result.total_duration_ms == 1500
