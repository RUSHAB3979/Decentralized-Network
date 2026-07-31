# API Reference (MVP)

Base URL (local): `http://localhost:8080`

All JSON payloads are validated with shared Zod schemas from `packages/contracts`.

## Health

### `GET /health`

Response:

```json
{
  "ok": true,
  "providers": 1,
  "jobs": 2
}
```

## Provider Heartbeat

### `POST /v1/providers/heartbeat`

Request body:

```json
{
  "providerId": "provider-local-1",
  "timestamp": "2026-08-01T00:00:00.000Z",
  "capability": {
    "gpuModel": "RTX-4070",
    "gpuVramGb": 12,
    "cpuCores": 12,
    "ramGb": 32,
    "supportsNvenc": true,
    "supportsQuickSync": false,
    "supportsGaming": true,
    "supportsCompute": true
  },
  "metrics": {
    "region": "us-east-1",
    "avgRttMs": 28,
    "jitterMs": 4,
    "packetLossPct": 0.2,
    "cpuLoadPct": 35,
    "gpuLoadPct": 40
  }
}
```

Success response:

```json
{
  "ok": true,
  "providerId": "provider-local-1"
}
```

## Match Endpoints

### `POST /v1/match/gaming`

Request body:

```json
{
  "requesterId": "req-1",
  "region": "us-east-1",
  "maxLatencyMs": 80
}
```

Success response:

```json
{
  "providerId": "provider-local-1",
  "region": "us-east-1",
  "avgRttMs": 23.5,
  "supportsEncoder": true
}
```

### `POST /v1/match/compute`

Request body:

```json
{
  "requesterId": "req-2",
  "region": "us-east-1",
  "minCpuCores": 8,
  "minRamGb": 16,
  "requireGpu": true,
  "minGpuVramGb": 8
}
```

Success response:

```json
{
  "providerId": "provider-local-1",
  "region": "us-east-1",
  "cpuCores": 12,
  "ramGb": 32,
  "gpuModel": "RTX-4070",
  "gpuVramGb": 12
}
```

## Compute Jobs

### `POST /v1/jobs`

Request body:

```json
{
  "requesterId": "req-3",
  "imageRef": "ghcr.io/acme/render:latest",
  "command": ["blender", "-b", "scene.blend", "-f", "1"],
  "region": "us-east-1",
  "minCpuCores": 8,
  "minRamGb": 16,
  "requireGpu": true,
  "minGpuVramGb": 8,
  "timeoutSec": 3600
}
```

Success response (`202 Accepted`):

```json
{
  "jobId": "job_11111111-2222-3333-4444-555555555555",
  "status": "running",
  "providerId": "provider-local-1"
}
```

When no provider matches immediately:

```json
{
  "jobId": "job_11111111-2222-3333-4444-555555555555",
  "status": "queued",
  "providerId": null
}
```

### `GET /v1/jobs/:id`

Success response:

```json
{
  "id": "job_11111111-2222-3333-4444-555555555555",
  "status": "running",
  "createdAt": "2026-08-01T00:00:00.000Z",
  "providerId": "provider-local-1",
  "request": {
    "requesterId": "req-3",
    "imageRef": "ghcr.io/acme/render:latest",
    "command": ["blender", "-b", "scene.blend", "-f", "1"],
    "region": "us-east-1",
    "minCpuCores": 8,
    "minRamGb": 16,
    "requireGpu": true,
    "minGpuVramGb": 8,
    "timeoutSec": 3600
  }
}
```

## Error Behavior

- `400 Bad Request`: schema validation failed.
- `404 Not Found`:
  - no suitable provider found (match endpoints)
  - unknown job id (`GET /v1/jobs/:id`)

Validation error shape:

```json
{
  "error": {
    "formErrors": [],
    "fieldErrors": {
      "region": ["String must contain at least 2 character(s)"]
    }
  }
}
```
