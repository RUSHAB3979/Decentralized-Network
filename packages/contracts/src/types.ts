export type ServiceType = "gaming" | "compute";

export interface ProviderCapability {
  gpuModel?: string;
  gpuVramGb?: number;
  cpuCores: number;
  ramGb: number;
  supportsNvenc: boolean;
  supportsQuickSync: boolean;
  supportsGaming: boolean;
  supportsCompute: boolean;
}

export interface ProviderMetrics {
  region: string;
  avgRttMs: number;
  jitterMs: number;
  packetLossPct: number;
  cpuLoadPct: number;
  gpuLoadPct: number;
}
