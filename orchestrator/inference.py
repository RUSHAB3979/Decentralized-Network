"""Security-sensitive helpers for the managed-inference gateway.

Customer API keys terminate at the orchestrator. Nothing in this module sends
an Authorization header onward to a provider machine.

This module used to also run the model, via a `run_chat` that called Ollama on
the orchestrator's own host. That helper is gone, and its absence is the point:
inference now happens on the provider's machine, dispatched through the job
queue in main.py and executed by agent/worker.py. A local runner left sitting
here would be one import away from silently turning rented inference back into
inference-on-the-server, with every test still green.
"""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass

API_KEY_MARKER = "nf_demo_"
API_KEY_PREFIX_LENGTH = 16


@dataclass(frozen=True)
class IssuedApiKey:
    secret: str
    prefix: str
    digest: str


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
