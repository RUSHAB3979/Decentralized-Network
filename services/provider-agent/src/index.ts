import { ProviderHeartbeatSchema } from "../../../packages/contracts/src/index.js";
import { config } from "./config.js";

function bounded(base: number, delta: number, min = 0, max = 100): number {
  const value = base + (Math.random() * 2 - 1) * delta;
  return Math.max(min, Math.min(max, Number(value.toFixed(2))));
}

function buildHeartbeat() {
  return {
    providerId: config.providerId,
    timestamp: new Date().toISOString(),
    capability: config.capability,
    metrics: {
      region: config.region,
      avgRttMs: bounded(28, 12, 5, 160),
      jitterMs: bounded(4, 3, 0, 30),
      packetLossPct: bounded(0.2, 0.4, 0, 3),
      cpuLoadPct: bounded(36, 20),
      gpuLoadPct: bounded(41, 30)
    }
  };
}

async function sendHeartbeat() {
  const payload = buildHeartbeat();
  const parse = ProviderHeartbeatSchema.safeParse(payload);
  if (!parse.success) {
    throw new Error(`Invalid heartbeat payload: ${parse.error.message}`);
  }

  const response = await fetch(`${config.orchestratorUrl}/v1/providers/heartbeat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(parse.data)
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(`Heartbeat failed (${response.status}): ${body}`);
  }
}

async function run() {
  console.log(
    `provider-agent starting (id=${config.providerId}, region=${config.region}, orchestrator=${config.orchestratorUrl})`
  );

  while (true) {
    try {
      await sendHeartbeat();
      console.log(`${new Date().toISOString()} heartbeat sent`);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      console.error(`${new Date().toISOString()} heartbeat error: ${message}`);
    }

    await new Promise((resolve) => setTimeout(resolve, config.heartbeatSec * 1000));
  }
}

void run();
