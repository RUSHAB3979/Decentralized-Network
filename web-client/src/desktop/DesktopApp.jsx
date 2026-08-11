import React, { useCallback, useEffect, useState } from 'react';
import {
  AlertTriangle,
  Boxes,
  Cpu,
  HardDrive,
  Loader2,
  MonitorCog,
  Power,
  ServerCog,
  Thermometer,
} from 'lucide-react';

// How often the window re-reads the machine. Three seconds is frequent enough
// that VRAM and utilisation feel live while a job runs, and cheap enough that
// the poll is invisible: a snapshot is one nvidia-smi call and two localhost
// requests.
const POLL_MS = 3000;

const STATUS_TONE = {
  idle: ['bg-emerald-300', 'text-emerald-300', 'border-emerald-300/25'],
  busy: ['bg-blue-400', 'text-blue-300', 'border-blue-300/25'],
  draining: ['bg-amber-300', 'text-amber-300', 'border-amber-300/25'],
  starting: ['bg-slate-400', 'text-slate-400', 'border-white/10'],
  stopped: ['bg-slate-500', 'text-slate-500', 'border-white/10'],
  error: ['bg-red-400', 'text-red-300', 'border-red-300/25'],
};

const Card = ({ icon: Icon, title, accent = 'text-slate-500', children }) => (
  <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5">
    <div className="flex items-center gap-2">
      <Icon className={`h-4 w-4 ${accent}`} />
      <h2 className="font-mono text-[9px] uppercase tracking-[0.18em] text-slate-600">{title}</h2>
    </div>
    <div className="mt-4">{children}</div>
  </section>
);

const Row = ({ label, value, mono = false }) => (
  <div className="flex items-baseline justify-between gap-4 border-b border-white/[0.04] py-2 last:border-0">
    <span className="shrink-0 text-[11px] text-slate-600">{label}</span>
    <span className={`truncate text-right text-[11px] text-slate-300 ${mono ? 'font-mono' : ''}`}>
      {value}
    </span>
  </div>
);

const Bar = ({ used, total }) => {
  const pct = total > 0 ? Math.min(100, Math.round((used / total) * 100)) : 0;
  return (
    <div className="mt-3">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/[0.06]">
        <div className="h-full rounded-full bg-emerald-300/70" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-1.5 font-mono text-[9px] text-slate-600">
        {used} / {total} MB VRAM ({pct}%)
      </p>
    </div>
  );
};

export default function DesktopApp() {
  const [data, setData] = useState(null);
  const [bridgeError, setBridgeError] = useState(null);

  const refresh = useCallback(async () => {
    try {
      const next = await window.pywebview.api.snapshot();
      setData(next);
      setBridgeError(null);
    } catch (error) {
      // The bridge failing is different from the machine being unhealthy, and
      // conflating them would show a green node while the window is actually
      // blind. Say which one broke.
      setBridgeError(String(error));
    }
  }, []);

  useEffect(() => {
    let timer;
    const start = () => {
      refresh();
      timer = setInterval(refresh, POLL_MS);
    };
    // pywebview injects its API asynchronously; reading it on first paint is a
    // race that usually loses.
    if (window.pywebview?.api) start();
    else window.addEventListener('pywebviewready', start, { once: true });
    return () => clearInterval(timer);
  }, [refresh]);

  const toggle = async () => {
    await window.pywebview.api.set_accepting(!data.node.accepts_work);
    refresh();
  };

  if (!data) {
    return (
      <div className="flex h-screen items-center justify-center gap-3 bg-[#08090a] text-slate-600">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-xs">Reading this machine...</span>
      </div>
    );
  }

  const { host, gpu, ollama, node, rentable } = data;
  const [dot, text, border] = STATUS_TONE[node.status] ?? STATUS_TONE.stopped;

  return (
    <div className="min-h-screen bg-[#08090a] px-6 py-6 text-slate-100">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-medium tracking-[-0.02em] text-slate-100">{host.hostname}</h1>
          <p className="mt-0.5 font-mono text-[9px] uppercase tracking-[0.18em] text-slate-700">
            Provider node
          </p>
        </div>
        <div className={`flex items-center gap-2 rounded-full border px-3 py-1.5 ${border}`}>
          <span className={`h-1.5 w-1.5 rounded-full ${dot}`} />
          <span className={`text-[11px] font-medium ${text}`}>{node.status}</span>
        </div>
      </header>

      {bridgeError && (
        <p className="mt-4 rounded-lg border border-red-300/20 bg-red-300/[0.04] p-3 font-mono text-[10px] text-red-200/70">
          Lost contact with the agent: {bridgeError}
        </p>
      )}

      {!rentable && (
        <div className="mt-5 flex items-start gap-3 rounded-xl border border-amber-300/20 bg-amber-300/[0.03] p-4">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-300" />
          <div>
            <p className="text-xs font-medium text-amber-100/90">This machine cannot serve paid work</p>
            <p className="mt-1 text-[11px] leading-5 text-amber-100/50">
              {!gpu && 'No NVIDIA GPU was detected, so inference would run on the CPU at a fraction of the speed. '}
              {!ollama.reachable && 'The Ollama runtime is not reachable. '}
              Earnings stay at zero until this is resolved.
            </p>
          </div>
        </div>
      )}

      <div className="mt-5 grid gap-4 lg:grid-cols-2">
        <Card icon={MonitorCog} title="Graphics" accent={gpu ? 'text-emerald-300' : 'text-slate-700'}>
          {gpu ? (
            <>
              <p className="text-sm font-medium text-slate-200">{gpu.name}</p>
              <Bar used={gpu.vram_used_mb ?? 0} total={gpu.vram_total_mb ?? 0} />
              <div className="mt-3">
                <Row label="Utilisation" value={gpu.utilisation_pct != null ? `${gpu.utilisation_pct}%` : 'n/a'} mono />
                <Row
                  label={<span className="flex items-center gap-1"><Thermometer className="h-3 w-3" /> Temperature</span>}
                  value={gpu.temperature_c != null ? `${gpu.temperature_c} C` : 'n/a'}
                  mono
                />
                <Row label="Driver" value={gpu.driver ?? 'n/a'} mono />
              </div>
            </>
          ) : (
            <p className="text-[11px] leading-5 text-slate-600">
              No NVIDIA GPU detected. <span className="text-slate-500">nvidia-smi</span> is not present,
              which means there is no CUDA device for the runtime to use.
            </p>
          )}
        </Card>

        <Card icon={ServerCog} title="Runtime" accent={ollama.reachable ? 'text-emerald-300' : 'text-red-300'}>
          {ollama.reachable ? (
            <>
              <p className="text-sm font-medium text-slate-200">Ollama</p>
              <p className="mt-1 font-mono text-[10px] text-slate-600">{ollama.version ?? 'version unknown'}</p>
              <div className="mt-3">
                <Row label="Models available" value={ollama.available.length} mono />
                <Row label="Loaded in VRAM" value={ollama.loaded.length} mono />
              </div>
              {ollama.loaded.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {ollama.loaded.map((m) => (
                    <span key={m.name} className="rounded-md border border-emerald-300/20 bg-emerald-300/[0.05] px-2 py-1 font-mono text-[9px] text-emerald-200/80">
                      {m.name}
                    </span>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-[11px] leading-5 text-slate-600">
              Not reachable on localhost:11434. The agent starts it automatically; if this
              persists, Ollama is probably not installed.
            </p>
          )}
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <Card icon={Boxes} title="Installed models">
          {ollama.available.length === 0 ? (
            <p className="text-[11px] text-slate-600">Nothing pulled yet.</p>
          ) : (
            <div className="max-h-40 overflow-y-auto pr-1">
              {ollama.available.map((m) => (
                <Row
                  key={m.name}
                  label={m.name}
                  // Cloud-hosted entries report zero bytes because they do not
                  // live on this disk, and showing "0 MB" would read as a
                  // corrupt download rather than a remote model.
                  value={m.size_mb ? `${m.size_mb} MB` : 'cloud'}
                  mono
                />
              ))}
            </div>
          )}
        </Card>

        <Card icon={Cpu} title="Host">
          <Row label="CPU" value={host.cpu.split(',')[0]} mono />
          <Row label="Logical cores" value={host.logical_cores} mono />
          <Row
            label={<span className="flex items-center gap-1"><HardDrive className="h-3 w-3" /> Memory</span>}
            value={host.ram_total_mb ? `${(host.ram_total_mb / 1024).toFixed(1)} GB` : 'n/a'}
            mono
          />
          <Row label="OS" value={host.os_version.replace(/[()]/g, '')} mono />
        </Card>
      </div>

      <footer className="mt-5 flex items-center justify-between rounded-xl border border-white/[0.07] bg-white/[0.018] p-4">
        <div>
          <p className="text-xs font-medium text-slate-300">
            {node.accepts_work ? 'Accepting new work' : 'Not accepting new work'}
          </p>
          <p className="mt-1 text-[10px] text-slate-600">{node.detail || 'No detail reported'}</p>
        </div>
        <button
          type="button"
          onClick={toggle}
          className={`inline-flex items-center gap-2 rounded-lg px-4 py-2.5 text-[11px] font-semibold transition ${
            node.accepts_work
              ? 'border border-white/[0.1] text-slate-400 hover:bg-white/[0.04]'
              : 'bg-emerald-300 text-[#08090a] hover:bg-emerald-200'
          }`}
        >
          <Power className="h-3.5 w-3.5" />
          {node.accepts_work ? 'Stop accepting' : 'Start accepting'}
        </button>
      </footer>
    </div>
  );
}
