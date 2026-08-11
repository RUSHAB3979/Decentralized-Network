"""Counting what is owed. HAND-BUILT - see README.md.

Failure mode: this is the quietest file in the repository. Undercounting is
invisible from the inside - every request succeeds, every customer is served,
and the provider is simply paid less than they earned. Overcounting is worse
and just as quiet. There is no exception either way, and no user who complains
in time for it to be caught.

Design notes worth settling before writing a line:

- Decide what is actually sold: output tokens, GPU-seconds, or wall-clock time.
  They diverge sharply. A slow model bills well per second and badly per token.
- Ollama's final streaming chunk carries `eval_count`, `eval_duration`,
  `prompt_eval_duration` and `load_duration`, all in nanoseconds. agent/bench.py
  already parses these; reuse the conversion rather than rewriting it.
- Cold-start time is real cost the provider pays and no customer asked for.
  Decide who absorbs it before the first payout, not after.
- Counters must survive a crash mid-request, because the provider machine is a
  gaming PC and will be put to sleep mid-job.
- Assume the reported numbers will eventually be disputed. Whatever is recorded
  has to be enough to reconstruct the bill without trusting this process.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Usage:
    """What one completed request is worth."""

    lease_id: str
    output_tokens: int
    gpu_seconds: float


def record(usage: Usage) -> None:
    """Persist usage durably enough to survive an unclean shutdown."""
    raise NotImplementedError


def pending() -> list[Usage]:
    """Usage recorded but not yet acknowledged by the orchestrator."""
    raise NotImplementedError


def acknowledge(usage: list[Usage]) -> None:
    """Drop usage the orchestrator has confirmed. Must be idempotent."""
    raise NotImplementedError
