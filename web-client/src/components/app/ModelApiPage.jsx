import React, { useEffect, useState } from 'react';
import {
  Activity,
  ArrowLeft,
  BookOpen,
  BrainCircuit,
  Check,
  Clipboard,
  Eye,
  EyeOff,
  Gauge,
  KeyRound,
  LoaderCircle,
  LockKeyhole,
  Play,
  Plus,
  RefreshCw,
  Server,
  ShieldCheck,
  Trash2,
  TriangleAlert,
} from 'lucide-react';
import { fetchProviderNodes } from '../../services/api';
import { storedToken } from '../../services/authApi';
import { useSession } from '../../hooks/useSession';
import {
  INFERENCE_BASE_URL,
  createApiKey,
  createChatCompletion,
  fetchInferenceModels,
  fetchInferenceUsage,
  listApiKeys,
  revokeApiKey,
} from '../../services/inferenceApi';

const TABS = [
  { id: 'setup', label: 'Setup', icon: Gauge },
  { id: 'keys', label: 'API keys', icon: KeyRound },
  { id: 'playground', label: 'Playground', icon: Play },
  { id: 'usage', label: 'Usage', icon: Activity },
  { id: 'docs', label: 'Quickstart', icon: BookOpen },
];

const formatDate = (value) => value
  ? new Date(value).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
  : 'Never';

const StatusPill = ({ good, children }) => (
  <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.16em] ${good ? 'border-emerald-300/20 bg-emerald-300/[0.05] text-emerald-300' : 'border-amber-300/20 bg-amber-300/[0.04] text-amber-300'}`}>
    <span className={`h-1.5 w-1.5 rounded-full ${good ? 'bg-emerald-300' : 'bg-amber-300'}`} />
    {children}
  </span>
);

const CopyButton = ({ value, label = 'Copy' }) => {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    await navigator.clipboard?.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };
  return (
    <button type="button" onClick={copy} className="inline-flex items-center gap-2 rounded-lg border border-white/[0.08] px-3 py-2 text-[10px] text-slate-500 hover:text-white">
      {copied ? <Check className="h-3.5 w-3.5 text-emerald-300" /> : <Clipboard className="h-3.5 w-3.5" />}
      {copied ? 'Copied' : label}
    </button>
  );
};

const SetupStep = ({ number, title, detail, complete }) => (
  <div className={`rounded-xl border p-4 ${complete ? 'border-emerald-300/15 bg-emerald-300/[0.025]' : 'border-white/[0.07] bg-[#0a0c12]'}`}>
    <div className="flex items-start gap-3">
      <span className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border font-mono text-[9px] ${complete ? 'border-emerald-300/20 text-emerald-300' : 'border-white/[0.08] text-slate-700'}`}>
        {complete ? <Check className="h-3.5 w-3.5" /> : number}
      </span>
      <div><p className="text-xs font-medium text-slate-300">{title}</p><p className="mt-1 text-[10px] leading-5 text-slate-600">{detail}</p></div>
    </div>
  </div>
);

const SetupTab = ({ gatewayReady, provider, apiKey, models, onOpenKeys }) => (
  <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
    <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6">
      <h2 className="text-sm font-medium text-slate-200">Request path readiness</h2>
      <p className="mt-1 text-[11px] text-slate-600">Every green step is required before this PC can receive an inference request.</p>
      <div className="mt-5 grid gap-3 md:grid-cols-2">
        <SetupStep number="01" title="Orchestrator gateway" detail="The browser can reach the API-key service and Postgres." complete={gatewayReady} />
        <SetupStep number="02" title="Provider heartbeat" detail={provider ? `${provider.hostname} is online and accepting work.` : 'Start one healthy provider agent and enable accepting work.'} complete={Boolean(provider)} />
        <SetupStep number="03" title="Customer API key" detail="The plaintext key stays with the customer; only its SHA-256 hash is stored." complete={Boolean(apiKey)} />
        <SetupStep number="04" title="Local model" detail={models.length ? `${models.map((model) => model.id).join(', ')} is available.` : 'Authenticate to read models advertised by the provider.'} complete={models.length > 0} />
      </div>
    </section>
    <aside className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.025] p-5">
      <Server className="h-5 w-5 text-cyan-300" />
      <p className="mt-4 font-mono text-[8px] uppercase tracking-[0.18em] text-cyan-300">Customer base URL</p>
      <code className="mt-3 block break-all rounded-lg border border-white/[0.07] bg-black/25 p-3 font-mono text-[11px] text-slate-300">{INFERENCE_BASE_URL}</code>
      <div className="mt-3"><CopyButton value={INFERENCE_BASE_URL} label="Copy base URL" /></div>
      <button type="button" onClick={onOpenKeys} className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-100 px-4 py-3 text-xs font-semibold text-[#08090a]"><KeyRound className="h-3.5 w-3.5" /> Configure API key</button>
    </aside>
  </div>
);

const ApiKeysTab = ({ keys, apiKey, onUseKey, onCreate, onRevoke, busy, error }) => {
  const [newKeyName, setNewKeyName] = useState('Shubh local demo');
  const [pastedKey, setPastedKey] = useState('');
  const [visible, setVisible] = useState(true);
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <section className="rounded-xl border border-white/[0.07] bg-white/[0.018]">
        <div className="border-b border-white/[0.06] p-5 sm:flex sm:items-end sm:justify-between sm:gap-4">
          <div><h2 className="text-sm font-medium text-slate-200">Real local API keys</h2><p className="mt-1 text-[11px] text-slate-600">The backend stores only a prefix and SHA-256 hash. A secret is shown once.</p></div>
          <div className="mt-4 flex gap-2 sm:mt-0"><input value={newKeyName} onChange={(event) => setNewKeyName(event.target.value)} aria-label="New API key name" className="min-w-0 rounded-lg border border-white/[0.08] bg-black/20 px-3 py-2.5 text-xs text-slate-300 outline-hidden focus:border-violet-300/30" /><button type="button" disabled={busy || !newKeyName.trim()} onClick={() => onCreate(newKeyName.trim())} className="inline-flex shrink-0 items-center gap-2 rounded-lg bg-slate-100 px-4 py-2.5 text-xs font-semibold text-[#08090a] disabled:opacity-40"><Plus className="h-3.5 w-3.5" /> Create</button></div>
        </div>

        {error && <p className="m-5 rounded-lg border border-red-300/20 bg-red-300/[0.04] p-3 text-[11px] text-red-200/70">{error}</p>}
        {apiKey && <div className="m-5 rounded-xl border border-amber-300/20 bg-amber-300/[0.035] p-5"><div className="flex items-start justify-between gap-4"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-amber-300">Copy this key now</p><p className="mt-2 text-[11px] text-amber-100/55">It will not be returned by the server again.</p></div><button type="button" onClick={() => setVisible((value) => !value)} className="text-amber-100/50">{visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}</button></div><div className="mt-4 flex gap-2 rounded-lg border border-white/[0.07] bg-black/25 p-3"><code className="min-w-0 flex-1 truncate font-mono text-[11px] text-slate-200">{visible ? apiKey : '*'.repeat(28)}</code><CopyButton value={apiKey} /></div></div>}

        <div className="border-y border-white/[0.06] p-5"><p className="text-xs font-medium text-slate-300">Use an existing key</p><p className="mt-1 text-[10px] text-slate-600">Paste a key after reloading the browser; secrets are not stored in browser storage.</p><div className="mt-3 flex gap-2"><input type="password" value={pastedKey} onChange={(event) => setPastedKey(event.target.value)} placeholder="nf_demo_..." className="min-w-0 flex-1 rounded-lg border border-white/[0.08] bg-black/20 px-3 py-2.5 font-mono text-xs text-slate-300 outline-hidden focus:border-violet-300/30" /><button type="button" disabled={!pastedKey.trim()} onClick={() => { onUseKey(pastedKey.trim()); setPastedKey(''); }} className="rounded-lg border border-white/[0.08] px-4 py-2.5 text-xs text-slate-400 disabled:opacity-40">Use key</button></div></div>

        {keys.length ? <div className="divide-y divide-white/[0.05]">{keys.map((key) => <div key={key.id} className="grid gap-4 p-5 sm:grid-cols-[minmax(0,1fr)_150px_150px_auto] sm:items-center"><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg border border-violet-300/15 bg-violet-300/[0.04] text-violet-300"><KeyRound className="h-4 w-4" /></span><div><p className="text-xs text-slate-300">{key.name}</p><p className="mt-1 font-mono text-[9px] text-slate-700">{key.key_prefix}...</p></div></div><div><p className="font-mono text-[8px] uppercase tracking-[0.14em] text-slate-700">Created</p><p className="mt-1 text-[10px] text-slate-500">{formatDate(key.created_at)}</p></div><div><p className="font-mono text-[8px] uppercase tracking-[0.14em] text-slate-700">Last used</p><p className="mt-1 text-[10px] text-slate-500">{formatDate(key.last_used_at)}</p></div><button type="button" aria-label={`Revoke ${key.name}`} onClick={() => onRevoke(key.id)} className="rounded-lg border border-white/[0.07] p-2 text-slate-700 hover:border-red-300/20 hover:text-red-300"><Trash2 className="h-3.5 w-3.5" /></button></div>)}</div> : <div className="p-8 text-center text-[11px] text-slate-600">No active keys yet.</div>}
      </section>
      <aside className="space-y-4"><div className="rounded-xl border border-emerald-300/15 bg-emerald-300/[0.025] p-5"><ShieldCheck className="h-5 w-5 text-emerald-300" /><h3 className="mt-4 text-sm text-slate-200">Key stops at the gateway</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">Your provider receives the prompt and model request, never the reusable customer key.</p></div><div className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><LockKeyhole className="h-5 w-5 text-violet-300" /><p className="mt-4 text-[11px] leading-5 text-slate-600">Key creation is deliberately restricted to requests originating from this PC while <span className="font-mono text-slate-400">LOCAL_DEMO_MODE=true</span>.</p></div></aside>
    </div>
  );
};

const PlaygroundTab = ({ apiKey, models, onUsageChanged }) => {
  const [model, setModel] = useState(models[0]?.id ?? '');
  const [prompt, setPrompt] = useState('Explain GPU rental in one short paragraph.');
  const [response, setResponse] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { if (!models.some((item) => item.id === model)) setModel(models[0]?.id ?? ''); }, [models, model]);

  const run = async () => {
    setBusy(true); setError(''); setResponse(null);
    try {
      const result = await createChatCompletion(apiKey, { model, messages: [{ role: 'user', content: prompt }], max_tokens: 160 });
      setResponse(result);
      onUsageChanged();
    } catch (requestError) {
      setError(requestError.message);
    } finally { setBusy(false); }
  };

  if (!apiKey) return <div className="rounded-xl border border-amber-300/15 bg-amber-300/[0.03] p-6 text-sm text-amber-100/70">Create or paste an API key before sending a request.</div>;
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
      <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6"><div className="flex items-center justify-between"><div><h2 className="text-sm text-slate-200">Send a real inference request</h2><p className="mt-1 text-[10px] text-slate-600">Queued for an online provider and run on their GPU. Your key stops at the orchestrator.</p></div><BrainCircuit className="h-5 w-5 text-violet-300" /></div><label className="mt-5 block text-[10px] text-slate-600">Model<select value={model} onChange={(event) => setModel(event.target.value)} className="mt-2 block w-full rounded-lg border border-white/[0.08] bg-[#0a0c12] p-3 font-mono text-xs text-slate-300 outline-hidden">{models.map((item) => <option key={item.id} value={item.id}>{item.id}</option>)}</select></label><label className="mt-4 block text-[10px] text-slate-600">Prompt<textarea value={prompt} onChange={(event) => setPrompt(event.target.value)} rows={7} className="mt-2 block w-full resize-y rounded-lg border border-white/[0.08] bg-[#0a0c12] p-3 text-xs leading-6 text-slate-300 outline-hidden focus:border-violet-300/30" /></label><button type="button" disabled={busy || !model || !prompt.trim()} onClick={run} className="mt-4 flex w-full items-center justify-center gap-2 rounded-lg bg-violet-300 px-4 py-3 text-xs font-semibold text-[#08090a] disabled:opacity-40">{busy ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}{busy ? 'Running on provider...' : 'Send request'}</button>{error && <p className="mt-3 rounded-lg border border-red-300/20 bg-red-300/[0.04] p-3 text-[11px] text-red-200/70">{error}</p>}</section>
      <section className="rounded-xl border border-white/[0.07] bg-[#0a0c12] p-5 sm:p-6"><p className="font-mono text-[9px] uppercase tracking-[0.18em] text-slate-700">Provider response</p>{response ? <><p className="mt-5 whitespace-pre-wrap text-sm leading-7 text-slate-300">{response.choices[0]?.message?.content}</p><div className="mt-6 grid grid-cols-3 gap-2 border-t border-white/[0.06] pt-4 text-center">{[['Input', response.usage.prompt_tokens], ['Output', response.usage.completion_tokens], ['Total', response.usage.total_tokens]].map(([label, value]) => <div key={label}><p className="font-mono text-sm text-slate-300">{value}</p><p className="mt-1 text-[8px] uppercase tracking-[0.14em] text-slate-700">{label} tokens</p></div>)}</div></> : <div className="flex min-h-72 flex-col items-center justify-center text-center"><BrainCircuit className="h-7 w-7 text-slate-800" /><p className="mt-4 text-xs text-slate-600">The real model response will appear here.</p></div>}</section>
    </div>
  );
};

const UsageTab = ({ usage, apiKey }) => (
  <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">{[
    ['Completed requests', usage?.requests ?? 0],
    ['Input tokens', usage?.prompt_tokens ?? 0],
    ['Output tokens', usage?.completion_tokens ?? 0],
    ['Total tokens', usage?.total_tokens ?? 0],
    ['Provider time', `${usage?.total_duration_ms ?? 0} ms`],
  ].map(([label, value]) => <div key={label} className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><p className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">{label}</p><p className="mt-3 text-2xl text-slate-200">{apiKey ? value : '-'}</p></div>)}</div>
);

const DocsTab = ({ model }) => {
  const code = `$env:NODEFORGE_API_KEY = "nf_demo_your_key_here"\n\n$headers = @{ Authorization = "Bearer $env:NODEFORGE_API_KEY" }\n$body = @{\n  model = "${model || 'tinyllama:latest'}"\n  messages = @(\n    @{ role = "user"; content = "Hello from the rented GPU" }\n  )\n} | ConvertTo-Json -Depth 4\n\nInvoke-RestMethod -Method Post \`\n  -Uri "${INFERENCE_BASE_URL}/chat/completions" \`\n  -Headers $headers -ContentType "application/json" -Body $body`;
  return <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]"><section className="rounded-xl border border-white/[0.07] bg-[#0a0c12] p-5 sm:p-6"><div className="flex items-center justify-between gap-4"><div><h2 className="text-sm text-slate-200">PowerShell quickstart</h2><p className="mt-1 text-[10px] text-slate-600">Base URL and bearer-key format match an OpenAI-compatible gateway.</p></div><CopyButton value={code} label="Copy code" /></div><pre className="mt-5 overflow-x-auto rounded-lg border border-white/[0.06] bg-black/30 p-5 font-mono text-[11px] leading-6 text-slate-400"><code>{code}</code></pre></section><aside className="rounded-xl border border-amber-300/15 bg-amber-300/[0.025] p-5"><TriangleAlert className="h-5 w-5 text-amber-300" /><h3 className="mt-4 text-sm text-slate-200">Local demo boundary</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">This proves key authentication, provider readiness, model execution, and usage evidence on one PC. Do not expose port 8080 to the internet yet: provider credentials, TLS, rate limits, billing, isolation, and failover are still future work.</p></aside></div>;
};

export default function ModelApiPage({ onNavigate }) {
  const session = useSession();
  const [activeTab, setActiveTab] = useState('setup');
  const [gatewayStatus, setGatewayStatus] = useState('loading');
  const [provider, setProvider] = useState(null);
  const [keys, setKeys] = useState([]);
  const [apiKey, setApiKey] = useState('');
  const [models, setModels] = useState([]);
  const [usage, setUsage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const refreshPublicState = async () => {
    try {
      // The registry needs a session now. `listApiKeys` reads the same stored
      // token internally, so both halves of this pair fail together if the
      // session has ended -- which is what the 401 branch below relies on.
      const [keyResult, nodeResult] = await Promise.all([
        listApiKeys(),
        fetchProviderNodes({ token: storedToken() }),
      ]);
      setKeys(keyResult.keys ?? []);
      setGatewayStatus('ok');
      // "Accepting" needs both liveness and the node's own consent. A provider
      // that is online but draining is not capacity, and showing it as one
      // would promise a request this page cannot fulfil.
      setProvider(nodeResult.ok ? nodeResult.nodes.find((node) => node.liveness === 'online' && node.accepts_work) ?? null : null);
    } catch (requestError) {
      // A dead session is not a gateway fault. Signing the user out here is the
      // honest response: leaving them on a dashboard whose every panel 401s
      // reads as the site being broken, and re-entering a password fixes it.
      if (requestError.status === 401) {
        session.invalidate();
        return;
      }
      setGatewayStatus('error');
      setError(requestError.message);
    }
  };

  const useKey = async (secret) => {
    setApiKey(secret); setError(''); setBusy(true);
    try {
      const [modelResult, usageResult] = await Promise.all([fetchInferenceModels(secret), fetchInferenceUsage(secret)]);
      setModels(modelResult.data ?? []);
      setUsage(usageResult);
    } catch (requestError) {
      setModels([]); setUsage(null); setError(requestError.message);
    } finally { setBusy(false); }
  };

  useEffect(() => { refreshPublicState(); }, []);

  const create = async (name) => {
    setBusy(true); setError('');
    try {
      const created = await createApiKey(name);
      await refreshPublicState();
      await useKey(created.key);
    } catch (requestError) { setError(requestError.message); setBusy(false); }
  };

  const revoke = async (keyId) => {
    setBusy(true); setError('');
    try { await revokeApiKey(keyId); setApiKey(''); setModels([]); setUsage(null); await refreshPublicState(); }
    catch (requestError) { setError(requestError.message); }
    finally { setBusy(false); }
  };

  const refreshUsage = async () => {
    if (!apiKey) return;
    try { setUsage(await fetchInferenceUsage(apiKey)); }
    catch (requestError) {
      // Clear rather than keep the previous totals. A stale number presented as
      // current is worse than no number: it is specific, plausible, and wrong.
      setUsage(null);
      setError(requestError.message);
    }
  };
  const selectedModel = models[0]?.id ?? '';

  return (
    <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
      <button type="button" onClick={() => onNavigate('/app')} className="flex items-center gap-2 text-[11px] text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> Marketplace overview</button>
      <section className="relative mt-6 overflow-hidden rounded-2xl border border-white/[0.07] bg-[radial-gradient(circle_at_top_right,rgba(167,139,250,0.12),transparent_35%),#0c0e16] p-7 sm:p-9"><div className="relative grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px] lg:items-end"><div><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-violet-300/15 bg-violet-300/[0.04] text-violet-300"><BrainCircuit className="h-5 w-5" /></span><p className="mt-6 font-mono text-[9px] uppercase tracking-[0.22em] text-violet-300">Managed inference</p><h1 className="mt-3 max-w-3xl text-3xl font-medium tracking-[-0.04em] text-slate-100 sm:text-5xl">Rent this GPU through one authenticated API</h1><p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">Create a customer key and call an OpenAI-compatible base URL. The orchestrator queues the request for an online provider, whose agent runs it on its own GPU and returns the result. Your key never leaves the orchestrator.</p></div><div className="rounded-xl border border-white/[0.08] bg-black/20 p-5"><div className="flex flex-wrap gap-2"><StatusPill good={gatewayStatus === 'ok'}>{gatewayStatus === 'ok' ? 'Gateway ready' : 'Gateway unavailable'}</StatusPill><StatusPill good={Boolean(provider)}>{provider ? 'Provider accepting' : 'Provider waiting'}</StatusPill></div><p className="mt-4 break-all font-mono text-[10px] text-slate-500">{INFERENCE_BASE_URL}</p><button type="button" onClick={refreshPublicState} className="mt-4 inline-flex items-center gap-2 text-[10px] text-slate-600 hover:text-white"><RefreshCw className="h-3.5 w-3.5" /> Refresh readiness</button></div></div></section>
      <div className="mt-6 overflow-x-auto border-b border-white/[0.06]"><div className="flex min-w-max gap-1">{TABS.map((tab) => <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 border-b px-4 py-3 text-[11px] ${activeTab === tab.id ? 'border-violet-300 text-slate-100' : 'border-transparent text-slate-600 hover:text-slate-300'}`}><tab.icon className="h-3.5 w-3.5" />{tab.label}</button>)}</div></div>
      <div className="mt-6">
        {activeTab === 'setup' && <SetupTab gatewayReady={gatewayStatus === 'ok'} provider={provider} apiKey={apiKey} models={models} onOpenKeys={() => setActiveTab('keys')} />}
        {activeTab === 'keys' && <ApiKeysTab keys={keys} apiKey={apiKey} onUseKey={useKey} onCreate={create} onRevoke={revoke} busy={busy} error={error} />}
        {activeTab === 'playground' && <PlaygroundTab apiKey={apiKey} models={models} onUsageChanged={refreshUsage} />}
        {activeTab === 'usage' && <UsageTab usage={usage} apiKey={apiKey} />}
        {activeTab === 'docs' && <DocsTab model={selectedModel} />}
      </div>
    </div>
  );
}
