"""Security-sensitive helpers for the local managed-inference gateway.

Customer API keys terminate at the orchestrator. Nothing in this module sends
an Authorization header to Ollama or to a provider machine.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from dataclasses import dataclass

import httpx

API_KEY_MARKER = "nf_demo_"
API_KEY_PREFIX_LENGTH = 16
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_INFERENCE_TIMEOUT_S = 120.0


@dataclass(frozen=True)
class IssuedApiKey:
    secret: str
    prefix: str
    digest: str


@dataclass(frozen=True)
class OllamaResult:
    content: str
    prompt_tokens: int
    completion_tokens: int
    finish_reason: str
    total_duration_ms: int | None


def issue_api_key() -> IssuedApiKey:
    """Create a customer key whose plaintext is returned exactly once."""
    secret = f"{API_KEY_MARKER}{secrets.token_urlsafe(32)}"
    return IssuedApiKey(
        secret=secret,
        prefix=secret[:API_KEY_PREFIX_LENGTH],
        digest=hash_api_key(secret),
    )


def hash_api_key(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def api_key_prefix(secret: str) -> str:
    return secret[:API_KEY_PREFIX_LENGTH]


def bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise ValueError("missing Authorization header")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        raise ValueError("use Authorization: Bearer <api-key>")
    return token.strip()


def ollama_url() -> str:
    return (os.getenv("LOCAL_OLLAMA_URL") or DEFAULT_OLLAMA_URL).rstrip("/")


def inference_timeout_s() -> float:
    try:
        return max(5.0, float(os.getenv("INFERENCE_TIMEOUT_SEC", "120")))
    except ValueError:
        return DEFAULT_INFERENCE_TIMEOUT_S


def run_chat(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float | None,
    max_tokens: int | None,
    client: httpx.Client | None = None,
) -> OllamaResult:
    """Run one non-streaming chat request against the local provider runtime."""
    options: dict[str, float | int] = {}
    if temperature is not None:
        options["temperature"] = temperature
    if max_tokens is not None:
        options["num_predict"] = max_tokens

    payload: dict = {"model": model, "messages": messages, "stream": False}
    if options:
        payload["options"] = options

    owns_client = client is None
    active_client = client or httpx.Client()
    try:
        response = active_client.post(
            f"{ollama_url()}/api/chat",
            json=payload,
            timeout=inference_timeout_s(),
        )
        response.raise_for_status()
        body = response.json()
    finally:
        if owns_client:
            active_client.close()

    message = body.get("message") or {}
    duration_ns = body.get("total_duration")
    return OllamaResult(
        content=str(message.get("content") or ""),
        prompt_tokens=max(0, int(body.get("prompt_eval_count") or 0)),
        completion_tokens=max(0, int(body.get("eval_count") or 0)),
        finish_reason="stop" if body.get("done", True) else "length",
        total_duration_ms=(
            max(0, int(duration_ns // 1_000_000))
            if isinstance(duration_ns, int)
            else None
        ),
    )
