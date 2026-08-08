import type {
  ComputeMatchRequest,
  GamingMatchRequest,
  ProviderHeartbeat
} from "@market/contracts";
import type { ProviderRecord } from "./state.js";

function scoreGaming(p: ProviderHeartbeat, req: GamingMatchRequest): number {
  if (!p.capability.supportsGaming) return Number.NEGATIVE_INFINITY;
  if (p.metrics.region !== req.region) return Number.NEGATIVE_INFINITY;
  if (p.metrics.avgRttMs > req.maxLatencyMs) return Number.NEGATIVE_INFINITY;

  const encoderBoost = p.capability.supportsNvenc || p.capability.supportsQuickSync ? 15 : 0;
  const loadPenalty = p.metrics.cpuLoadPct * 0.4 + p.metrics.gpuLoadPct * 0.6;
  const latencyPenalty = p.metrics.avgRttMs * 1.2 + p.metrics.jitterMs * 0.8;

  return 100 + encoderBoost - loadPenalty - latencyPenalty;
}

function scoreCompute(p: ProviderHeartbeat, req: ComputeMatchRequest): number {
  if (!p.capability.supportsCompute) return Number.NEGATIVE_INFINITY;
  if (p.metrics.region !== req.region) return Number.NEGATIVE_INFINITY;
  if (p.capability.cpuCores < req.minCpuCores) return Number.NEGATIVE_INFINITY;
  if (p.capability.ramGb < req.minRamGb) return Number.NEGATIVE_INFINITY;

  if (req.requireGpu) {
    const vram = p.capability.gpuVramGb ?? 0;
    if (!p.capability.gpuModel || vram < (req.minGpuVramGb ?? 0)) {
      return Number.NEGATIVE_INFINITY;
    }
  }

  const capacityScore = p.capability.cpuCores * 6 + p.capability.ramGb * 1.2 + (p.capability.gpuVramGb ?? 0) * 2;
  const loadPenalty = p.metrics.cpuLoadPct * 0.7 + p.metrics.gpuLoadPct * 0.7;

  return capacityScore - loadPenalty;
}

export function selectGamingProvider(records: ProviderRecord[], req: GamingMatchRequest): ProviderRecord | null {
  let best: ProviderRecord | null = null;
  let bestScore = Number.NEGATIVE_INFINITY;

  for (const record of records) {
    const score = scoreGaming(record, req);
    if (score > bestScore) {
      bestScore = score;
      best = record;
    }
  }

  return best;
}

export function selectComputeProvider(records: ProviderRecord[], req: ComputeMatchRequest): ProviderRecord | null {
  let best: ProviderRecord | null = null;
  let bestScore = Number.NEGATIVE_INFINITY;

  for (const record of records) {
    const score = scoreCompute(record, req);
    if (score > bestScore) {
      bestScore = score;
      best = record;
    }
  }

  return best;
}
