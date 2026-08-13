import React from 'react';
import {
  Activity,
  ArrowRight,
  Cpu,
  Database,
  Gauge,
  Radio,
  Server,
  Thermometer,
} from 'lucide-react';
import { NODE_POLL_MS } from '../../hooks/useProviderNodes';

const ABSENT = 'Not reported';

function mostRecentNode(nodes) {
  return [...nodes].sort((left, right) => {
    const leftTime = left.last_heartbeat_at ? new Date(left.last_heartbeat_at).getTime() : 0;
    const rightTime = right.last_heartbeat_at ? new Date(right.last_heartbeat_at).getTime() : 0;
    return rightTime - leftTime;
  })[0] ?? null;
}

function heartbeatAge(heartbeatAt, serverTime) {
  if (!heartbeatAt) return 'Never received';
  const reference = serverTime ? new Date(serverTime).getTime() : Date.now();
  const seconds = Math.max(0, Math.round((reference - new Date(heartbeatAt).getTime()) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
  return `${Math.round(seconds / 3600)}h ago`;
}

function vramValue(node) {
  if (node?.vram_total_mb == null) return ABSENT;
  const used = node.vram_used_mb == null ? '?' : Math.round(node.vram_used_mb);
  return `${used} / ${Math.round(node.vram_total_mb)} MB`;
}

const FLOW_TONES = {
  good: 'border-emerald-300/20 bg-emerald-300/[0.035] text-emerald-300',
  waiting: 'border-amber-300/20 bg-amber-300/[0.035] text-amber-300',
  error: 'border-red-300/20 bg-red-300/[0.035] text-red-300',
  quiet: 'border-white/[0.08] bg-white/[0.02] text-slate-500',
};

const FlowStep = ({ icon: Icon, eyebrow, title, detail, tone }) => (
  <div className={`min-w-0 flex-1 rounded-xl border p-4 ${FLOW_TONES[tone]}`}>
    <div className="flex items-center gap-2">
      <Icon className="h-4 w-4 shrink-0" />
      <p className="font-mono text-[8px] uppercase tracking-[0.18em] opacity-70">{eyebrow}</p>
    </div>
    <p className="mt-3 truncate text-sm font-medium text-slate-200">{title}</p>
    <p className="mt-1 text-[10px] leading-5 text-slate-600">{detail}</p>
  </div>
);

const Metric = ({ icon: Icon, label, value, detail, accent = 'text-cyan-300' }) => (
  <div className="rounded-xl border border-white/[0.06] bg-[#090b11] p-4">
    <div className="flex items-center gap-2">
      <Icon className={`h-3.5 w-3.5 ${accent}`} />
      <p className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">{label}</p>
    </div>
    <p className="mt-3 font-mono text-sm text-slate-200">{value}</p>
    <p className="mt-1 text-[9px] text-slate-700">{detail}</p>
  </div>
);

export default function AgentHeartbeatPanel({ registry, onOpenNodes }) {
  const node = mostRecentNode(registry.nodes);
  const registryReady = registry.status === 'ok';
  const registryFailed = registry.status === 'error';
  const online = node?.liveness === 'online';
  const heartbeat = heartbeatAge(node?.last_heartbeat_at, registry.serverTime);

  const agentTitle = node?.hostname
    ?? (registryReady ? 'No agent enrolled' : 'Checking for an agent');
  const agentDetail = node
    ? `${node.agent_version ? `Agent v${node.agent_version}` : 'Provider agent'} - ${node.liveness.replace('_', ' ')}`
    : 'Start the desktop provider app to register this PC.';
  const agentTone = node ? (online ? 'good' : 'waiting') : 'quiet';

  const registryTitle = registryFailed
    ? 'Registry unavailable'
    : registryReady
      ? 'Registry connected'
      : 'Connecting';
  const registryDetail = registryFailed
    ? 'The browser cannot read the orchestrator right now.'
    : 'Receives /providers/heartbeat and stores the latest sample.';

  return (
    <section className="overflow-hidden rounded-xl border border-cyan-300/15 bg-[radial-gradient(circle_at_top_right,rgba(34,211,238,0.07),transparent_35%),#0a0c13] p-5 sm:p-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-cyan-300">
            <Radio className={`h-4 w-4 ${online ? 'animate-pulse' : ''}`} />
            <p className="font-mono text-[9px] uppercase tracking-[0.2em]">Live provider network</p>
          </div>
          <h2 className="mt-3 text-lg font-medium text-slate-100">Agent heartbeat and telemetry</h2>
          <p className="mt-1 max-w-2xl text-[11px] leading-5 text-slate-600">
            This is the real path used by Shubh's provider-agent work. The browser refreshes the registry every {NODE_POLL_MS / 1000} seconds; it does not invent values when hardware is missing.
          </p>
        </div>
        <button
          type="button"
          onClick={onOpenNodes}
          className="shrink-0 rounded-lg border border-cyan-300/15 bg-cyan-300/[0.04] px-4 py-2.5 text-[10px] font-medium text-cyan-200 transition hover:bg-cyan-300/[0.08]"
        >
          Open all node telemetry
        </button>
      </div>

      <div className="mt-6 flex flex-col items-stretch gap-2 lg:flex-row lg:items-center">
        <FlowStep
          icon={Cpu}
          eyebrow="1. Provider PC"
          title={agentTitle}
          detail={agentDetail}
          tone={agentTone}
        />
        <div className="flex items-center justify-center gap-2 py-1 text-slate-700 lg:px-1 lg:py-0">
          <span className="font-mono text-[8px] uppercase tracking-[0.14em]">heartbeat</span>
          <ArrowRight className="h-3.5 w-3.5 rotate-90 lg:rotate-0" />
        </div>
        <FlowStep
          icon={Database}
          eyebrow="2. Orchestrator"
          title={registryTitle}
          detail={registryDetail}
          tone={registryFailed ? 'error' : registryReady ? 'good' : 'waiting'}
        />
        <div className="flex items-center justify-center gap-2 py-1 text-slate-700 lg:px-1 lg:py-0">
          <span className="font-mono text-[8px] uppercase tracking-[0.14em]">poll</span>
          <ArrowRight className="h-3.5 w-3.5 rotate-90 lg:rotate-0" />
        </div>
        <FlowStep
          icon={Server}
          eyebrow="3. Web app"
          title={registryFailed ? 'Waiting for data' : 'Telemetry visible'}
          detail="Reads /providers/nodes and renders the latest honest state."
          tone={registryFailed ? 'waiting' : registryReady ? 'good' : 'quiet'}
        />
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <Metric
          icon={Activity}
          label="Last heartbeat"
          value={node ? heartbeat : ABSENT}
          detail={node ? `Offline after ${registry.ttlSeconds ?? '?'}s without a heartbeat` : 'No provider sample received'}
          accent={online ? 'text-emerald-300' : 'text-amber-300'}
        />
        <Metric
          icon={Gauge}
          label="GPU load"
          value={node?.gpu_utilisation_pct == null ? ABSENT : `${node.gpu_utilisation_pct}%`}
          detail={node?.gpu_name ?? 'No NVIDIA GPU detected'}
        />
        <Metric
          icon={Database}
          label="VRAM"
          value={vramValue(node)}
          detail="Used / total from the agent"
        />
        <Metric
          icon={Thermometer}
          label="Temperature"
          value={node?.temperature_c == null ? ABSENT : `${node.temperature_c} C`}
          detail="Latest NVIDIA telemetry sample"
          accent={node?.temperature_c > 75 ? 'text-red-300' : 'text-cyan-300'}
        />
        <Metric
          icon={Server}
          label="Runtime"
          value={node ? (node.ollama_reachable ? 'Ollama online' : 'Ollama offline') : ABSENT}
          detail={node ? `${node.local_models?.length ?? 0} local models` : 'Waiting for an agent'}
          accent={node?.ollama_reachable ? 'text-emerald-300' : 'text-slate-600'}
        />
      </div>
    </section>
  );
}
