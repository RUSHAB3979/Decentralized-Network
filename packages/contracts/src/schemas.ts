import { z } from "zod";

export const ProviderCapabilitySchema = z.object({
  gpuModel: z.string().optional(),
  gpuVramGb: z.number().int().nonnegative().optional(),
  cpuCores: z.number().int().positive(),
  ramGb: z.number().int().positive(),
  supportsNvenc: z.boolean(),
  supportsQuickSync: z.boolean(),
  supportsGaming: z.boolean(),
  supportsCompute: z.boolean()
});

export const ProviderMetricsSchema = z.object({
  region: z.string().min(2),
  avgRttMs: z.number().nonnegative(),
  jitterMs: z.number().nonnegative(),
  packetLossPct: z.number().min(0).max(100),
  cpuLoadPct: z.number().min(0).max(100),
  gpuLoadPct: z.number().min(0).max(100)
});

export const ProviderHeartbeatSchema = z.object({
  providerId: z.string().min(3),
  timestamp: z.string().datetime(),
  capability: ProviderCapabilitySchema,
  metrics: ProviderMetricsSchema
});

export const GamingMatchRequestSchema = z.object({
  requesterId: z.string().min(3),
  region: z.string().min(2),
  maxLatencyMs: z.number().positive().default(80)
});

export const ComputeMatchRequestSchema = z.object({
  requesterId: z.string().min(3),
  region: z.string().min(2),
  minCpuCores: z.number().int().positive(),
  minRamGb: z.number().int().positive(),
  requireGpu: z.boolean().default(false),
  minGpuVramGb: z.number().int().nonnegative().optional()
});

export const ComputeJobSubmitSchema = z.object({
  requesterId: z.string().min(3),
  imageRef: z.string().min(3),
  command: z.array(z.string()).min(1),
  region: z.string().min(2),
  minCpuCores: z.number().int().positive(),
  minRamGb: z.number().int().positive(),
  requireGpu: z.boolean().default(false),
  minGpuVramGb: z.number().int().nonnegative().optional(),
  timeoutSec: z.number().int().positive().max(86400)
});

export type ProviderHeartbeat = z.infer<typeof ProviderHeartbeatSchema>;
export type GamingMatchRequest = z.infer<typeof GamingMatchRequestSchema>;
export type ComputeMatchRequest = z.infer<typeof ComputeMatchRequestSchema>;
export type ComputeJobSubmit = z.infer<typeof ComputeJobSubmitSchema>;
