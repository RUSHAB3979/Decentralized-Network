# Session Flow

## Purpose

This document describes how a gaming session moves through the current system,
from provider readiness to stream setup and teardown.

It tracks the real flow we have now:

- provider app detects whether the machine can serve work
- the provider agent reports telemetry to the orchestrator
- the orchestrator stores node state and exposes it to the UI
- the session transport uses WebRTC with TURN fallback when direct P2P fails

## Current product shape

The project is currently organised around two user-visible paths:

1. **Provider readiness and telemetry**
   - the provider app shows local hardware/runtime state
   - the agent sends registration and heartbeat data to the orchestrator
   - the provider console reads live node state from the orchestrator

2. **Interactive gaming transport**
   - WebRTC carries audio/video/input
   - STUN is used for direct peer discovery
   - TURN relays traffic when NAT/firewall rules block direct delivery

The separate transport decision is documented in
[docs/spikes/transport-decision.md](../spikes/transport-decision.md).

## Provider readiness flow

```
Provider machine
  -> agent collects telemetry
  -> reporter registers node
  -> reporter heartbeats capability + metrics
  -> orchestrator stores node state
  -> provider UI shows live status
```

### What the agent reports

The agent reports the fields defined in `orchestrator/models.py`:

- identity:
  - `node_id`
- capability:
  - hostname
  - OS version
  - CPU
  - logical cores
  - RAM
  - GPU name
  - VRAM total
  - GPU driver
  - agent version
- live metrics:
  - GPU utilisation
  - VRAM used
  - temperature
  - Ollama reachability
  - Ollama version
  - locally available models

### What the orchestrator does with it

The orchestrator:

- validates the payload
- upserts the node during registration
- updates the node during heartbeat
- computes liveness from `last_heartbeat_at`
- returns the current node list to the provider console

## Session flow

The interactive gaming path is:

```
User selects a title
  -> orchestrator finds a suitable provider
  -> session is created
  -> signaling exchanges SDP and ICE
  -> WebRTC establishes media and input channels
  -> provider encodes locally
  -> client decodes and displays the stream
```

## Transport rules

### Media plane

- Use **WebRTC** for interactive media.
- Use **DTLS-SRTP** for encrypted media transport.
- Prefer direct P2P when NAT allows it.
- Fall back to **TURN** when direct connectivity fails.

### Control plane

- Use HTTP for registration, node listing, and session metadata.
- Use WebSocket signaling for SDP and ICE exchange.

## BYOL and cache warming

For the gaming track, the current product direction is:

- pre-cache game files on providers
- never pre-supply licences
- the renter uses their own account to satisfy ownership checks

That gives us:

- zero-download sessions for cached titles
- legal separation between cached files and licence execution
- a path for scheduled cache warming without storing credentials

## What “ready” means

On the provider console, “ready” means:

- the machine has the required hardware/runtime
- the node is registered and heartbeating
- the provider is online and accepting work

It does **not** mean:

- the game is licensed by the marketplace
- the title is necessarily warm in VRAM
- the node is guaranteed to be routable without TURN

## Failure handling

The system should stay honest about three failure classes:

1. **Healthy**
   - orchestrator returns `200`
   - provider state is current

2. **Degraded**
   - orchestrator is up but its database is down
   - health returns `503`

3. **Unreachable**
   - orchestrator is down or not listening
   - the agent gets a request error and retries with backoff

Those three cases must remain distinct in the UI and logs.

## What remains for later phases

- full session signalling implementation
- warm-cache scheduling
- actual game/session launch orchestration
- session teardown and cleanup automation
- richer provider reputation and earnings surfaces

## Summary

The current flow is:

`Provider machine -> Agent telemetry -> Orchestrator registry -> UI`

and for live sessions:

`User -> Session request -> Signaling -> WebRTC media path -> Play`

This document should stay aligned with the live code as transport, telemetry,
and provider onboarding continue to evolve.
