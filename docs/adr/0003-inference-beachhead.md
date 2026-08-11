# ADR 0003 — Use inference as the beachhead market

| Field | Value |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-11 |
| **Owner** | [@RUSHAB3979](https://github.com/RUSHAB3979) (R1 Architect) |
| **Supersedes** | Cloud gaming as the beachhead market |

---

## Context

The company was formed around a peer-to-peer marketplace for idle consumer GPU
capacity. Cloud gaming was the first market chosen for that capacity.

Cloud gaming's binding constraint is interactive latency. A session needs
WebRTC negotiation, ICE candidate selection, TURN relay fallback, and a
capture-encode-transport pipeline, all tuned to a frame budget of roughly 16
ms. Every one of those areas is on ADR 0002's hand-built list because failures
degrade a session silently instead of throwing an error.

LLM inference does not have a frame budget. A request takes as long as it takes
and uses request/response over HTTP. WebRTC, ICE, TURN, capture, and video
encoding therefore leave the critical path.

The provider app now exists and runs. `agent/app.py` provides a system tray
icon, a supervised Ollama process, and a WebView2 desktop dashboard. This is a
working base for supplying inference capacity from consumer Windows machines.

## Decision

**Rent idle consumer GPUs for LLM inference as the beachhead market.**

This changes the first customer, not the company. The long-term thesis remains
a peer-to-peer marketplace for idle consumer GPU capacity. Cloud gaming is
deferred, not abandoned.

Ollama is the runtime that ships. vLLM on native Windows currently requires
CUDA 13 and an RTX 6000 Ada or newer. Its supported path on the consumer cards
this marketplace is built to aggregate is WSL2. Ollama runs natively on Windows
today and fits the provider app that already exists.

## Consequences

The initial product no longer depends on interactive media transport. The
WebRTC negotiation, ICE selection, TURN fallback, capture, encoding, and frame
budget work can wait. HTTP request/response and the existing provider app make
the first end-to-end capacity test smaller.

The competitive field is harder. Vast.ai, RunPod, Together, and the
hyperscalers' spot and serverless tiers are established and heavily funded.
Cloud gaming had fewer direct peer-to-peer competitors. Per-GPU revenue on
consumer cards is also lower for inference than for gaming.

The moat changes from transport engineering to aggregation, cold-start latency,
and trust. The marketplace has to combine heterogeneous and intermittently
available machines, place work without long model-loading delays, and make
customers willing to send workloads to consumer-owned hardware.

Inference capacity claims are easy to get wrong in the optimistic direction.
`agent/bench.py` originally summed per-request throughput derived from Ollama's
`eval_duration`, which excludes queue time. That overstated aggregate
throughput by 4.3x because it described a parallel server that did not exist.
The benchmark now divides total tokens by batch wall-clock time. Pricing built
on an overstated capacity number inherits the same error, so capacity and
revenue claims require wall-clock measurement under realistic concurrency.

Gaming-specific transport knowledge is postponed. Deferring it reduces the
first product's critical path but also delays evidence that consumer networks
can support the original gaming use case.

## Alternatives considered

**Keep cloud gaming as the beachhead.** Rejected because its first useful test
requires the latency-sensitive surface that ADR 0002 identifies as hand-built.
That work remains relevant if gaming is resumed, but it is not required to test
whether idle consumer GPUs can be supplied and rented.

**Ship vLLM as the Windows provider runtime.** Rejected because its native
Windows requirements exclude the consumer cards this marketplace intends to
aggregate, while its supported consumer path adds WSL2 as a deployment
requirement.

**Abandon gaming and become an inference-only company.** Rejected because the
decision concerns market entry, not the long-term marketplace thesis. Gaming
remains a possible use of the same aggregated GPU supply after the inference
market has tested aggregation, cold starts, and trust.
