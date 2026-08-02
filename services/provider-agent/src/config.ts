export const config = {
  providerId: process.env.PROVIDER_ID ?? "provider-local-1",
  orchestratorUrl: process.env.ORCHESTRATOR_URL ?? "http://localhost:8080",
  region: process.env.REGION ?? "us-east-1",
  heartbeatSec: Number(process.env.HEARTBEAT_SEC ?? 15),
  capability: {
    gpuModel: process.env.GPU_MODEL ?? "RTX-4070",
    gpuVramGb: Number(process.env.GPU_VRAM_GB ?? 12),
    cpuCores: Number(process.env.CPU_CORES ?? 12),
    ramGb: Number(process.env.RAM_GB ?? 32),
    supportsNvenc: (process.env.SUPPORTS_NVENC ?? "true") === "true",
    supportsQuickSync: (process.env.SUPPORTS_QUICKSYNC ?? "false") === "true",
    supportsGaming: (process.env.SUPPORTS_GAMING ?? "true") === "true",
    supportsCompute: (process.env.SUPPORTS_COMPUTE ?? "true") === "true"
  }
};
