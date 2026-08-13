# Transport Decision

## Decision

Use **WebRTC** for interactive session media.

## Why WebRTC

WebRTC is the best fit for the gaming track because it gives us, in one stack:

- built-in encryption on the media path
- low-latency UDP transport
- NAT traversal with STUN/TURN fallback
- browser-native playback
- a well-known signaling model

That combination matters for this project because the provider node and the
player may sit behind ordinary home routers, hotel Wi-Fi, or carrier NAT. A
solution that only works on easy networks is not enough for a marketplace.

## Options considered

### 1. WebRTC

Keep.

Reasons:

- browser support is first-class
- direct peer-to-peer is possible when NAT allows it
- TURN gives a safe fallback when it does not
- the media path is already encrypted by default
- it matches the current product direction for cloud gaming

### 2. Raw UDP / custom RTP

Drop.

Reasons:

- we would have to build NAT traversal ourselves
- browser support is not direct
- encryption, congestion control, and reconnect logic become our problem
- the implementation cost is far higher than the product value at this stage

### 3. WebSocket / HTTP streaming

Drop for the gaming track.

Reasons:

- TCP head-of-line blocking hurts interactive latency
- video frame delivery becomes bursty under loss
- it is not a good fit for controller input + live video

### 4. Cloud-hosted remote desktop over a vendor SDK

Drop for the core platform.

Reasons:

- locks us into a provider-specific stack
- reduces control over cost and routing
- makes the project less portable and less explainable as a final-year build

## Final architecture

### Media plane

- WebRTC for audio/video/input
- DTLS-SRTP for encryption
- UDP where possible
- TURN relay fallback when direct peer-to-peer fails

### Control plane

- HTTP for registration, session creation, and metadata
- WebSocket signaling for SDP and ICE exchange

## Latency budget

This is the target budget for a gaming session path.

| Hop | Budget |
|---|---|
| Capture on provider | 5-10 ms |
| Encode on provider | 5-12 ms |
| Network transit direct | 10-25 ms |
| Network transit relayed | 20-50 ms |
| Decode on client | 5-12 ms |
| Display / scanout | 5-16 ms |

### Direct path target

Target end-to-end glass-to-glass latency:

- **40-60 ms** on a good direct path

### TURN path target

Target end-to-end glass-to-glass latency:

- **60-100 ms** on a relayed path

That is still acceptable for many casual and single-player use cases, but it
is the expensive path.

## TURN cost estimate

We need a working estimate for relayed sessions because TURN is the cost
center.

### Assumptions

- average relayed media rate: **8 Mbps**
- relay fraction: **15%**
- average session length: **1 hour**
- relay overhead applies to both directions, so the effective served traffic is
  roughly the same order as the media rate above for a first-pass estimate
- egress price: **$0.05 per GB** as a placeholder planning number

### Arithmetic

1. Convert bitrate to hourly data:

   - `8 Mbps = 8 / 8 = 1 MB/s`
   - `1 MB/s * 3600 s = 3600 MB/hour`
   - `3600 MB/hour ≈ 3.6 GB/hour`

2. Apply relay fraction:

   - `3.6 GB/hour * 15% = 0.54 GB/hour of relayed traffic per active session`

3. Apply egress price:

   - `0.54 GB * $0.05/GB = $0.027 per relayed session-hour`

### Interpretation

At this assumed rate, TURN costs roughly:

- **2.7 cents per relayed session-hour**

That sounds small per session, but it becomes material when:

- the relay fraction rises above 15%
- sessions run for long durations
- bitrate increases for higher resolution or frame rate

## Relay fraction assumption

Use **10-20%** as the planning range for TURN fallback.

Why this range:

- many consumer networks allow direct connections
- symmetric NAT, restrictive firewalls, and some mobile/hotel networks do not
- the exact number depends on provider geography, ISP mix, and how many users
  are on corporate or campus networks

For planning, use **15%** as the midpoint until real telemetry says otherwise.

## Codec and encoder assumptions

### Provider-side encoding

Assume:

- H.264 as the default compatibility codec
- hardware encoding when available
- software fallback only for diagnostics or non-revenue paths

### Why H.264 first

- widest browser compatibility
- lower integration risk
- good enough for the first working product

### Later options

- HEVC for higher quality per bit if browser/device support is acceptable
- AV1 only when hardware support and encode cost make sense for the fleet

## GPU requirements

The provider GPU should support:

- real-time hardware encode
- stable encoder session availability
- acceptable thermal headroom under sustained load

For the current project, that means:

- NVIDIA hardware with NVENC is the cleanest first target
- GPU telemetry should be used to decide whether the node is actually
  rentable before offering a gaming session

## What this means for the codebase

### Build now

- WebRTC signaling
- ICE gathering
- STUN/TURN configuration
- provider-side encoder detection
- latency instrumentation

### Do not build yet

- custom media transport
- provider-owned credential sharing
- any architecture that requires the provider to expose their LAN directly

## Conclusion

WebRTC is the right transport for the gaming track because it gives us the
lowest-risk path to interactive streaming with browser playback, encryption,
and NAT traversal. TURN is expected to be a minority fallback, but it must be
budgeted explicitly because it is the expensive case.
