"""Measure what this machine is actually worth as an inference provider.

This is v0 of the provider agent, and it deliberately does the smallest useful
thing: find out whether the hardware we expect to recruit  -  a consumer gaming
GPU running Ollama on Windows  -  can serve a small model fast enough for the
economics in ADR 0002 to work.

It is a measurement, not a service. There is no orchestrator connection, no
credential, no lease and no metering here, because none of those can be
designed sensibly until the numbers below exist.

Why Ollama and not vLLM: vLLM's native Windows build requires CUDA 13 and an
RTX 6000 Ada or newer. On a 3080 or 4090 the supported path is WSL2, which
reintroduces exactly the onboarding friction a one-click Windows provider app
exists to remove. Ollama runs natively on consumer Windows, so it is the
runtime we can actually ship  -  and therefore the only runtime whose throughput
number transfers to the real product.

Dependencies: none beyond what agent/requirements.txt already pins. GPU facts
come from nvidia-smi, which ships with the driver, and Ollama speaks HTTP.
That file is a security boundary (see its header) and this script is not a
reason to widen it.

Usage:
    python agent/bench.py                      # defaults to qwen2.5:7b
    python agent/bench.py --model llama3.1:8b
    python agent/bench.py --json results.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, asdict, field

import httpx

OLLAMA = "http://127.0.0.1:11434"

# The prompt is fixed so runs are comparable across machines. It asks for a
# long answer on purpose: we are measuring sustained generation, and a model
# that stops after twenty tokens tells us nothing about throughput.
PROMPT = (
    "Explain how a GPU executes a matrix multiplication, in detail, "
    "covering memory hierarchy and parallelism."
)
MAX_TOKENS = 256


@dataclass
class Gpu:
    name: str
    vram_total_mb: int
    driver: str


@dataclass
class RunResult:
    """One generation. Durations are seconds; Ollama reports nanoseconds."""

    output_tokens: int
    load_s: float
    prompt_eval_s: float
    eval_s: float
    total_s: float
    ttft_s: float

    @property
    def tokens_per_s(self) -> float:
        return self.output_tokens / self.eval_s if self.eval_s > 0 else 0.0


@dataclass
class Report:
    gpu: Gpu | None
    model: str
    cold_start_s: float
    concurrency: dict[int, float] = field(default_factory=dict)
    per_run: dict[int, list[float]] = field(default_factory=dict)


def detect_gpu() -> Gpu | None:
    """Read the GPU from nvidia-smi. Absent driver is a normal outcome, not a crash."""
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,driver_version",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        ).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    if not out:
        return None
    # Multi-GPU machines print one line per device; v0 measures the first.
    name, vram, driver = (part.strip() for part in out.splitlines()[0].split(","))
    return Gpu(name=name, vram_total_mb=int(vram), driver=driver)


async def ensure_model(client: httpx.AsyncClient, model: str) -> None:
    """Pull the model if it is not already present, streaming progress."""
    tags = await client.get(f"{OLLAMA}/api/tags", timeout=30)
    tags.raise_for_status()
    have = {m["name"] for m in tags.json().get("models", [])}
    if model in have:
        print(f"model  : {model} (already present)")
        return

    print(f"model  : {model} not present  -  pulling")
    async with client.stream(
        "POST", f"{OLLAMA}/api/pull", json={"model": model}, timeout=None
    ) as response:
        response.raise_for_status()
        last = ""
        async for line in response.aiter_lines():
            if not line:
                continue
            status = json.loads(line).get("status", "")
            if status != last:
                print(f"         {status}")
                last = status


async def generate(client: httpx.AsyncClient, model: str, keep_alive: str = "5m") -> RunResult:
    """One streamed generation, returning Ollama's own timing counters.

    Time-to-first-token is measured here rather than derived, because it is what
    a customer perceives and it includes queueing that Ollama's counters omit.
    """
    started = time.perf_counter()
    ttft = 0.0
    final: dict = {}

    async with client.stream(
        "POST",
        f"{OLLAMA}/api/generate",
        json={
            "model": model,
            "prompt": PROMPT,
            "stream": True,
            "keep_alive": keep_alive,
            "options": {"num_predict": MAX_TOKENS, "temperature": 0},
        },
        timeout=None,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if not ttft and chunk.get("response"):
                ttft = time.perf_counter() - started
            if chunk.get("done"):
                final = chunk

    ns = 1_000_000_000
    return RunResult(
        output_tokens=final.get("eval_count", 0),
        load_s=final.get("load_duration", 0) / ns,
        prompt_eval_s=final.get("prompt_eval_duration", 0) / ns,
        eval_s=final.get("eval_duration", 0) / ns,
        total_s=final.get("total_duration", 0) / ns,
        ttft_s=ttft,
    )


async def measure_cold_start(client: httpx.AsyncClient, model: str) -> float:
    """Unload the model, then measure how long the next request waits for it.

    This is the number that makes provider churn expensive. A node that drops
    and returns pays it again, which is why ADR 0002's scheduling notes treat
    'which models are warm where' as first-class state rather than a detail.
    """
    # keep_alive=0 evicts the model from VRAM as soon as this request finishes.
    await generate(client, model, keep_alive="0")
    await asyncio.sleep(2)  # let the eviction actually land
    return (await generate(client, model)).load_s


async def measure_concurrency(
    client: httpx.AsyncClient, model: str, level: int
) -> list[RunResult]:
    """Fire `level` generations at once and return every result.

    Aggregate throughput, not single-stream speed, is what the utilisation
    maths needs  -  one request never saturates a GPU.
    """
    return await asyncio.gather(*(generate(client, model) for _ in range(level)))


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:7b")
    parser.add_argument(
        "--concurrency",
        default="1,4,16",
        help="comma-separated levels to test (default: 1,4,16)",
    )
    parser.add_argument("--json", help="also write the report to this path")
    args = parser.parse_args()

    levels = [int(x) for x in args.concurrency.split(",") if x.strip()]

    gpu = detect_gpu()
    if gpu is None:
        print("gpu    : no nvidia-smi  -  CPU or non-NVIDIA. Numbers will not be")
        print("         representative of a provider machine.")
    else:
        print(f"gpu    : {gpu.name}  {gpu.vram_total_mb} MB  driver {gpu.driver}")

    async with httpx.AsyncClient() as client:
        try:
            await client.get(f"{OLLAMA}/api/tags", timeout=5)
        except httpx.RequestError as exc:
            # Distinguish 'not installed' from 'installed but not running'  -
            # collapsing them into one error throws away the useful half.
            print(f"error  : no Ollama at {OLLAMA} ({exc.__class__.__name__})")
            print("         Install from https://ollama.com/download, then re-run.")
            return 1

        await ensure_model(client, args.model)

        print("\nmeasuring cold start (model evicted, then reloaded)...")
        cold = await measure_cold_start(client, args.model)
        print(f"cold start: {cold:6.2f} s")

        report = Report(gpu=gpu, model=args.model, cold_start_s=cold)

        print("\nmeasuring throughput")
        print(f"{'conc':>5}  {'agg tok/s':>10}  {'per-stream':>11}  {'p95 ttft':>9}")
        for level in levels:
            runs = await measure_concurrency(client, args.model, level)
            aggregate = sum(r.tokens_per_s for r in runs)
            per_stream = aggregate / level
            ttfts = sorted(r.ttft_s for r in runs)
            p95 = ttfts[min(int(len(ttfts) * 0.95), len(ttfts) - 1)]
            report.concurrency[level] = aggregate
            report.per_run[level] = [r.tokens_per_s for r in runs]
            print(f"{level:>5}  {aggregate:>10.1f}  {per_stream:>11.1f}  {p95:>8.2f}s")

    peak = max(report.concurrency.values()) if report.concurrency else 0.0
    print(f"\npeak aggregate throughput: {peak:.1f} tok/s")
    print("cost per 1M tokens at $X/hr  =  X / (peak * 3600) * 1e6")
    print(f"  ... at $0.20/hr  =  ${0.20 / (peak * 3600) * 1e6:.3f}" if peak else "")

    # Deliberately no pass/fail threshold here. What counts as acceptable
    # throughput is a pricing decision, not a measurement, and a generated
    # harness that asserts the wrong bound reports success. ADR 0002 puts that
    # judgement on the founder; write it in once the pricing model exists.

    if args.json:
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(asdict(report), handle, indent=2)
        print(f"\nwrote {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
