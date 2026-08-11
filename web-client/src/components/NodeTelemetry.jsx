// Real provider telemetry, read from the orchestrator's node registry.
//
// This component used to render MOCK_NODES with randomly fluctuating
// temperatures. Everything invented is gone (M1 item 6). What is shown here now
// comes from a desktop agent that registered itself and is heartbeating, or the
// component says so plainly.
//
// The three non-obvious rules it follows:
//
// 1. Absent is rendered as absent. A provider with no NVIDIA GPU reports null
//    for every GPU field, and null renders as an em dash, never as 0. A zero
//    would read as "idle GPU" on a machine that has no GPU at all.
// 2. A failed fetch is never rendered as an empty fleet. See fetchProviderNodes
//    in services/api.js.
// 3. Liveness comes from the server, which derives it from the last heartbeat.
//    The browser does not decide who is online; a client with a wrong clock
//    would otherwise disagree with the marketplace about what is available.
import React from 'react';
import { Server, RefreshCw, AlertTriangle, Inbox } from 'lucide-react';
import { useProviderNodes, NODE_POLL_MS } from '../hooks/useProviderNodes';

const POLL_MS = NODE_POLL_MS;

// A dash, not a zero. See rule 1 above.
const ABSENT = '—';
const show = (value, suffix = '') => (value === null || value === undefined ? ABSENT : `${value}${suffix}`);

const gb = (mb) => (mb === null || mb === undefined ? ABSENT : `${(mb / 1024).toFixed(1)} GB`);

function relativeTime(iso) {
    if (!iso)
        return 'never';
    const seconds = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 1000));
    if (seconds < 60)
        return `${seconds}s ago`;
    if (seconds < 3600)
        return `${Math.round(seconds / 60)}m ago`;
    return `${Math.round(seconds / 3600)}h ago`;
}

const TONES = {
    emerald: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    amber: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    slate: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

// Why a node is not taking work matters more than the fact that it isn't, and
// the reasons have different fixes: a provider who chose to drain needs
// nothing, a dead Ollama needs restarting, a machine with no GPU needs to be
// told it will never qualify. An earlier version of this component collapsed
// all of them into "draining", which put the label "draining" beside the
// agent's own detail line "ready for work" on a GPU-less laptop — a display
// that is not merely unhelpful but self-contradictory.
//
// 'never_seen' is likewise kept separate from 'offline': it means the agent
// registered and its heartbeat loop then failed, which is a broken install
// rather than a sleeping machine.
function nodeState(node) {
    if (node.liveness === 'never_seen') {
        return { label: 'no heartbeat', tone: 'red', reason: 'Registered, but has never checked in.' };
    }
    if (node.liveness === 'offline') {
        return { label: 'offline', tone: 'slate', reason: 'No heartbeat within the TTL.' };
    }
    if (node.accepts_work) {
        return { label: 'online', tone: 'emerald', reason: node.detail || null, pulse: true };
    }
    if (node.status === 'draining' || node.status === 'stopped') {
        return { label: node.status, tone: 'amber', reason: 'Provider is not accepting new work.' };
    }
    if (!node.ollama_reachable) {
        return { label: 'runtime down', tone: 'red', reason: 'Ollama is not responding on this machine.' };
    }
    if (!node.gpu_name) {
        return { label: 'no GPU', tone: 'slate', reason: 'No NVIDIA GPU, so this node cannot serve inference.' };
    }
    return { label: 'not accepting', tone: 'amber', reason: node.detail || null };
}

const StateBadge = ({ label, tone, pulse }) => (<span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${TONES[tone]}`}>
    {pulse && (<span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full rounded-full opacity-75 animate-ping bg-emerald-400"/>
        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400"/>
      </span>)}
    {label}
  </span>);

const GpuUtilBar = ({ pct }) => {
    if (pct === null || pct === undefined) {
        return <span className="text-xs text-slate-500">{ABSENT}</span>;
    }
    const color = pct >= 90
        ? 'bg-red-500'
        : pct >= 70
            ? 'bg-amber-500'
            : pct >= 40
                ? 'bg-indigo-500'
                : 'bg-emerald-500';
    return (<div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 rounded-full bg-slate-700/60 overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ease-out ${color}`} style={{ width: `${pct}%` }}/>
      </div>
      <span className="text-xs font-mono text-slate-300 w-10 text-right">{pct}%</span>
    </div>);
};

const Placeholder = ({ icon: Icon, tone, title, children }) => (<div className="px-4 py-10 flex flex-col items-center gap-3 text-center">
    <Icon className={`w-6 h-6 ${tone}`}/>
    <p className="text-sm text-white">{title}</p>
    <div className="text-xs text-slate-400 max-w-md">{children}</div>
  </div>);

const NodeTelemetry = () => {
    const result = useProviderNodes(POLL_MS);
    const nodes = result.nodes;
    const online = nodes.filter((n) => n.liveness === 'online').length;

    return (<div className="space-y-6">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
            <Server className="w-5 h-5 text-indigo-400"/>
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Provider nodes</h2>
            <p className="text-xs text-slate-400">
              {result.status === 'ok'
            ? `${online} online of ${nodes.length} enrolled · offline after ${result.ttlSeconds ?? '?'}s without a heartbeat`
            : 'Live registrations from the desktop provider app'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
          <RefreshCw className={`w-3.5 h-3.5 ${result.status === 'error' ? 'text-red-400' : 'text-emerald-400'} ${result.status === 'loading' ? 'animate-spin' : ''}`} style={{ animationDuration: '2s' }}/>
          <span className="text-xs font-mono text-slate-400">{POLL_MS / 1000}s</span>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-700/50 bg-slate-900/50 backdrop-blur-xs overflow-hidden">
        {result.status === 'error' ? (<Placeholder icon={AlertTriangle} tone="text-red-400" title={result.error}>
            Nothing is shown rather than a guess: an empty table here would be
            indistinguishable from a marketplace with no providers.
            {result.detail ? (<span className="block mt-2 font-mono text-[11px] text-slate-500 break-all">{result.detail}</span>) : null}
          </Placeholder>) : result.status === 'loading' ? (<Placeholder icon={RefreshCw} tone="text-slate-400 animate-spin" title="Reading the node registry…">
            Asking the orchestrator which providers have enrolled.
          </Placeholder>) : nodes.length === 0 ? (<Placeholder icon={Inbox} tone="text-slate-400" title="No providers have enrolled yet">
            Run the desktop app with <span className="font-mono text-slate-300">python -m agent.app</span>.
            It registers on start and heartbeats every few seconds; this table updates on its own.
          </Placeholder>) : (<div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-slate-700/50">
                {['Node', 'State', 'GPU', 'GPU Util', 'Thermals', 'Runtime', 'Last heartbeat'].map((heading) => (<th key={heading} className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                    {heading}
                  </th>))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {nodes.map((node) => {
            const tempHot = node.temperature_c !== null && node.temperature_c > 75;
            const state = nodeState(node);
            return (<tr key={node.node_id} className="hover:bg-slate-800/40 transition-colors">
                    {/* Node */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-xs text-white">{node.hostname}</span>
                        {/* Truncated because the id is 32 hex characters and
                            the full value is only ever needed for support. */}
                        <span className="font-mono text-[11px] text-slate-500" title={node.node_id}>
                          {node.node_id.slice(0, 12)}…
                        </span>
                      </div>
                    </td>

                    {/* State */}
                    <td className="px-4 py-3">
                      <StateBadge label={state.label} tone={state.tone} pulse={state.pulse}/>
                      {state.reason ? (<div className="text-[11px] text-slate-500 mt-1">{state.reason}</div>) : null}
                    </td>

                    {/* GPU */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-xs text-white">{node.gpu_name ?? 'No NVIDIA GPU'}</span>
                        <span className="text-xs text-slate-500">
                          {node.vram_total_mb === null || node.vram_total_mb === undefined
                    ? `${node.logical_cores ?? ABSENT} cores · ${gb(node.ram_total_mb)} RAM`
                    : `${gb(node.vram_used_mb)} / ${gb(node.vram_total_mb)} · driver ${show(node.gpu_driver)}`}
                        </span>
                      </div>
                    </td>

                    {/* GPU Util */}
                    <td className="px-4 py-3">
                      <GpuUtilBar pct={node.gpu_utilisation_pct}/>
                    </td>

                    {/* Thermals */}
                    <td className="px-4 py-3">
                      <span className={`font-mono text-sm font-medium ${node.temperature_c === null ? 'text-slate-500' : tempHot ? 'text-red-400' : 'text-emerald-400'}`}>
                        {show(node.temperature_c, '°C')}
                      </span>
                    </td>

                    {/* Runtime */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className={`text-xs ${node.ollama_reachable ? 'text-white' : 'text-slate-500'}`}>
                          {node.ollama_reachable ? (node.ollama_version ?? 'Ollama up') : 'Ollama down'}
                        </span>
                        {/* Local weights only. Ollama Cloud entries are
                            filtered out by the agent, so this count is capacity
                            this machine actually holds. */}
                        <span className="text-xs text-slate-500">
                          {node.local_models?.length ?? 0} local model{node.local_models?.length === 1 ? '' : 's'}
                        </span>
                      </div>
                    </td>

                    {/* Last heartbeat */}
                    <td className="px-4 py-3">
                      <span className="text-xs text-slate-400 font-mono" title={node.last_heartbeat_at ?? ''}>
                        {relativeTime(node.last_heartbeat_at)}
                      </span>
                    </td>
                  </tr>);
        })}
            </tbody>
          </table>
        </div>)}
      </div>
    </div>);
};
export default NodeTelemetry;
