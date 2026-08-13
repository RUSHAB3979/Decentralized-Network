# NVML Telemetry Spike

## Goal

Find out what GPU telemetry we can read from a real NVIDIA provider machine,
how expensive each read is, and which bits are safe to expose without
administrator rights.

## What this spike uses

- `nvidia-smi` if it exists on the machine
- `pynvml` only if it is already installed
- standard library code otherwise

No new runtime dependency was added to `agent/`. This spike lives in `docs/spikes/`
on purpose.

## Script

- [nvml-telemetry.py](./nvml-telemetry.py)

## What I found on this machine

This machine does **not** have an NVIDIA GPU available to the probe.
The script detected:

- no `nvidia-smi` response with GPU inventory
- no rentable NVIDIA device

That means this machine is useful for validating the negative path:

- the agent should not claim GPU capacity it does not have
- the UI should explain why the node cannot earn yet
- the spike still runs and exits cleanly on non-NVIDIA hardware

## Readability matrix

This matrix is the design target for a real NVIDIA provider box. It is what
the script is intended to confirm when run on the right hardware.

| Metric | NVML / nvidia-smi support | Admin needed? | Notes |
|---|---|---|---|
| GPU name | Yes | Usually no | Basic device identity should be readable without admin rights. |
| VRAM total | Yes | Usually no | `memory.total` is a standard read. |
| VRAM used | Yes | Usually no | `memory.used` is part of the normal telemetry set. |
| GPU utilisation | Yes | Usually no | `utilization.gpu` should be cheap to sample. |
| Temperature | Usually yes | Usually no | Some laptop / virtual GPUs may return `[N/A]`. |
| Power draw | Usually yes | Sometimes vendor-dependent | Not every device exposes a stable power sensor. |
| Fan speed | Sometimes | Sometimes no | Commonly unavailable on laptops and some OEM systems. |
| Encoder sessions | Sometimes | Usually no | Useful for gaming/streaming limits, but not guaranteed on every card. |

## Cost per sample

Target cost for a single read:

- `nvidia-smi` path: low tens of milliseconds
- NVML path: usually similar or faster

The important constraint is not the exact number on one machine, but that the
read can run every few seconds without becoming noticeable on a gaming system.

## Admin rights

The expectation for the provider app is that the basic read path should work as
a normal user.

If a metric needs admin rights on some machines, the agent should treat it as an
optional field rather than a hard failure.

## Non-NVIDIA and hybrid graphics

This spike is designed to answer these cases cleanly:

- no NVIDIA GPU
- AMD-only machine
- laptop with hybrid graphics

The correct behaviour is graceful degradation:

- report that the machine is not rentable for NVIDIA inference
- keep the rest of the app working
- do not throw a traceback for a normal hardware shape

## What remains to test on a real NVIDIA box

Run the script on a machine with an NVIDIA GPU and record:

- which metrics are populated
- which ones come back as `[N/A]`
- whether the read is stable under full GPU load
- whether the read time changes materially under load
- whether the encoder-session information is exposed on that card

## Conclusion

This spike is intentionally small. Its job is to prove the provider agent can
distinguish rentable and non-rentable machines and to define which telemetry is
safe to depend on before we wire anything into the heartbeat loop.
