import express from "express";
import {
  ComputeJobSubmitSchema,
  ComputeMatchRequestSchema,
  GamingMatchRequestSchema,
  ProviderHeartbeatSchema
} from "@market/contracts";
import { config } from "./config.js";
import { selectComputeProvider, selectGamingProvider } from "./matching.js";
import { jobs, providers } from "./state.js";

const app = express();
app.use(express.json());

function activeProviders() {
  const now = Date.now();
  const ttl = config.providerTtlMs;

  return [...providers.values()].filter((provider) => now - provider.lastSeenEpochMs <= ttl);
}

app.get("/health", (_req, res) => {
  res.json({
    ok: true,
    providers: activeProviders().length,
    jobs: jobs.size
  });
});

app.post("/v1/providers/heartbeat", (req, res) => {
  const parse = ProviderHeartbeatSchema.safeParse(req.body);
  if (!parse.success) {
    return res.status(400).json({ error: parse.error.flatten() });
  }

  const heartbeat = parse.data;
  providers.set(heartbeat.providerId, {
    ...heartbeat,
    lastSeenEpochMs: Date.now()
  });

  return res.json({ ok: true, providerId: heartbeat.providerId });
});

app.post("/v1/match/gaming", (req, res) => {
  const parse = GamingMatchRequestSchema.safeParse(req.body);
  if (!parse.success) {
    return res.status(400).json({ error: parse.error.flatten() });
  }

  const selected = selectGamingProvider(activeProviders(), parse.data);
  if (!selected) {
    return res.status(404).json({ error: "No suitable provider found" });
  }

  return res.json({
    providerId: selected.providerId,
    region: selected.metrics.region,
    avgRttMs: selected.metrics.avgRttMs,
    supportsEncoder: selected.capability.supportsNvenc || selected.capability.supportsQuickSync
  });
});

app.post("/v1/match/compute", (req, res) => {
  const parse = ComputeMatchRequestSchema.safeParse(req.body);
  if (!parse.success) {
    return res.status(400).json({ error: parse.error.flatten() });
  }

  const selected = selectComputeProvider(activeProviders(), parse.data);
  if (!selected) {
    return res.status(404).json({ error: "No suitable provider found" });
  }

  return res.json({
    providerId: selected.providerId,
    region: selected.metrics.region,
    cpuCores: selected.capability.cpuCores,
    ramGb: selected.capability.ramGb,
    gpuModel: selected.capability.gpuModel ?? null,
    gpuVramGb: selected.capability.gpuVramGb ?? null
  });
});

app.post("/v1/jobs", (req, res) => {
  const parse = ComputeJobSubmitSchema.safeParse(req.body);
  if (!parse.success) {
    return res.status(400).json({ error: parse.error.flatten() });
  }

  const match = selectComputeProvider(activeProviders(), {
    requesterId: parse.data.requesterId,
    region: parse.data.region,
    minCpuCores: parse.data.minCpuCores,
    minRamGb: parse.data.minRamGb,
    requireGpu: parse.data.requireGpu,
    minGpuVramGb: parse.data.minGpuVramGb
  });

  const id = `job_${crypto.randomUUID()}`;
  jobs.set(id, {
    id,
    status: match ? "running" : "queued",
    createdAt: new Date().toISOString(),
    providerId: match?.providerId,
    request: parse.data
  });

  return res.status(202).json({
    jobId: id,
    status: match ? "running" : "queued",
    providerId: match?.providerId ?? null
  });
});

app.get("/v1/jobs/:id", (req, res) => {
  const record = jobs.get(req.params.id);
  if (!record) {
    return res.status(404).json({ error: "Job not found" });
  }

  return res.json(record);
});

app.listen(config.port, () => {
  console.log(`orchestrator listening on :${config.port}`);
});
