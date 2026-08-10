import React, { useMemo, useState } from 'react';
import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  BrainCircuit,
  Check,
  ChevronRight,
  Clipboard,
  Clock3,
  Copy,
  Eye,
  EyeOff,
  KeyRound,
  LockKeyhole,
  Plus,
  Search,
  ShieldCheck,
  Trash2,
  X,
  Zap,
} from 'lucide-react';

const MODELS = [
  {
    id: 'preview/chat-8b',
    name: 'Chat 8B',
    family: 'Example catalog entry',
    type: 'Chat completions',
    context: '32K preview context',
    hardware: '16 GB+ VRAM profile',
    endpoint: '/v1/chat/completions',
    revision: 'Revision pin required',
    license: 'License review required',
    description: 'A representative general-purpose assistant profile for testing the managed inference product experience.',
    accent: 'cyan',
  },
  {
    id: 'preview/code-14b',
    name: 'Code 14B',
    family: 'Example catalog entry',
    type: 'Chat completions',
    context: '64K preview context',
    hardware: '24 GB+ VRAM profile',
    endpoint: '/v1/chat/completions',
    revision: 'Revision pin required',
    license: 'License review required',
    description: 'A representative code-focused deployment profile with a larger context window and higher GPU requirements.',
    accent: 'violet',
  },
  {
    id: 'preview/embed-small',
    name: 'Embed Small',
    family: 'Example catalog entry',
    type: 'Embeddings',
    context: '8K preview context',
    hardware: '8 GB+ VRAM profile',
    endpoint: '/v1/embeddings',
    revision: 'Revision pin required',
    license: 'License review required',
    description: 'A representative embedding endpoint for search, clustering, and retrieval-augmented applications.',
    accent: 'emerald',
  },
];

const TABS = [
  { id: 'catalog', label: 'Model catalog', icon: BrainCircuit },
  { id: 'keys', label: 'API keys', icon: KeyRound },
  { id: 'usage', label: 'Usage', icon: BarChart3 },
  { id: 'docs', label: 'Quickstart', icon: BookOpen },
];

const ACCENTS = {
  cyan: 'border-cyan-300/15 bg-cyan-300/[0.04] text-cyan-300',
  violet: 'border-violet-300/15 bg-violet-300/[0.04] text-violet-300',
  emerald: 'border-emerald-300/15 bg-emerald-300/[0.04] text-emerald-300',
};

const CODE_SAMPLE = `import OpenAI from "openai";

const client = new OpenAI({
  baseURL: "https://api.nodeforge.example/v1",
  apiKey: process.env.NODEFORGE_API_KEY,
});

const response = await client.chat.completions.create({
  model: "preview/chat-8b",
  messages: [{ role: "user", content: "Hello" }],
});`;

const ModelCard = ({ model, selected, onSelect }) => (
  <button
    type="button"
    onClick={() => onSelect(model)}
    className={`group w-full rounded-xl border p-5 text-left transition-all ${selected ? 'border-violet-300/30 bg-violet-300/[0.045]' : 'border-white/[0.07] bg-white/[0.018] hover:border-white/[0.14] hover:bg-white/[0.03]'}`}
  >
    <div className="flex items-start justify-between gap-4">
      <span className={`flex h-10 w-10 items-center justify-center rounded-xl border ${ACCENTS[model.accent]}`}><BrainCircuit className="h-[18px] w-[18px]" /></span>
      <span className="rounded-full border border-amber-300/15 bg-amber-300/[0.035] px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.16em] text-amber-200/70">Candidate</span>
    </div>
    <p className="mt-5 font-mono text-[9px] uppercase tracking-[0.2em] text-slate-700">{model.family}</p>
    <h3 className="mt-2 text-lg font-medium tracking-[-0.02em] text-slate-200">{model.name}</h3>
    <p className="mt-2 text-[11px] text-slate-500">{model.type} · {model.context}</p>
    <div className="mt-5 flex items-center justify-between border-t border-white/[0.05] pt-4 text-[10px]">
      <span className="text-slate-600">{model.hardware}</span>
      <span className="flex items-center gap-1 text-slate-400">Inspect <ChevronRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5" /></span>
    </div>
  </button>
);

const CatalogTab = ({ selectedModel, onSelectModel }) => {
  const [query, setQuery] = useState('');
  const filteredModels = useMemo(() => MODELS.filter((model) => `${model.name} ${model.type}`.toLowerCase().includes(query.toLowerCase())), [query]);

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <section>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 className="text-lg font-medium text-slate-200">Curated catalog preview</h2><p className="mt-1 text-[11px] text-slate-600">No model is commercially available until revision, license, runtime, and benchmark review pass.</p></div>
          <label className="relative block sm:w-64"><Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-700" /><input value={query} onChange={(event) => setQuery(event.target.value)} aria-label="Search model catalog" placeholder="Search models" className="h-9 w-full rounded-lg border border-white/[0.07] bg-white/[0.02] pl-9 pr-3 text-xs text-slate-200 outline-hidden placeholder:text-slate-700 focus:border-violet-300/30" /></label>
        </div>
        <div className="mt-5 grid gap-4 lg:grid-cols-3 xl:grid-cols-1 2xl:grid-cols-3">
          {filteredModels.map((model) => <ModelCard key={model.id} model={model} selected={model.id === selectedModel.id} onSelect={onSelectModel} />)}
        </div>
      </section>

      <aside className="rounded-xl border border-white/[0.07] bg-[#0b0d14] p-5 xl:sticky xl:top-[96px] xl:h-fit">
        <div className="flex items-start justify-between"><span className={`flex h-10 w-10 items-center justify-center rounded-xl border ${ACCENTS[selectedModel.accent]}`}><BrainCircuit className="h-[18px] w-[18px]" /></span><span className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Planning record</span></div>
        <h2 className="mt-5 text-xl font-medium text-slate-100">{selectedModel.name}</h2>
        <p className="mt-3 text-[12px] leading-6 text-slate-500">{selectedModel.description}</p>
        <div className="mt-5 space-y-3 border-y border-white/[0.06] py-5 text-[11px]">
          {[['Model ID', selectedModel.id], ['Endpoint', selectedModel.endpoint], ['Runtime', 'vLLM candidate'], ['Revision', selectedModel.revision], ['License', selectedModel.license]].map(([label, value]) => <div key={label} className="flex items-start justify-between gap-4"><span className="text-slate-700">{label}</span><span className="max-w-[210px] text-right font-mono text-[10px] text-slate-400">{value}</span></div>)}
        </div>
        <button type="button" onClick={() => document.getElementById('model-tabs')?.scrollIntoView({ behavior: 'smooth' })} className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-100 py-3 text-xs font-semibold text-[#08090a]">Deployment flow planned <Clock3 className="h-3.5 w-3.5" /></button>
      </aside>
    </div>
  );
};

const ApiKeysTab = () => {
  const [keys, setKeys] = useState([]);
  const [newKey, setNewKey] = useState('');
  const [visible, setVisible] = useState(true);
  const [copied, setCopied] = useState(false);

  const createPreviewKey = () => {
    const suffix = globalThis.crypto?.randomUUID?.().replaceAll('-', '').slice(0, 18) || Math.random().toString(36).slice(2, 20);
    const secret = `nf_preview_${suffix}`;
    setNewKey(secret);
    setVisible(true);
    setKeys([{ id: 'preview-key-01', name: 'Local preview key', prefix: `${secret.slice(0, 15)}…`, created: 'Just now', lastUsed: 'Never' }]);
  };

  const copyKey = async () => {
    await navigator.clipboard?.writeText(newKey);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
      <section className="rounded-xl border border-white/[0.07] bg-white/[0.018]">
        <div className="flex flex-col gap-4 border-b border-white/[0.06] p-5 sm:flex-row sm:items-center sm:justify-between"><div><h2 className="text-sm font-medium text-slate-200">API keys</h2><p className="mt-1 text-[11px] text-slate-600">Keys are marketplace-owned, scoped, prefix-indexed, hashed, and revocable in the planned backend.</p></div><button type="button" onClick={createPreviewKey} className="inline-flex items-center justify-center gap-2 rounded-lg bg-slate-100 px-4 py-2.5 text-xs font-semibold text-[#08090a]"><Plus className="h-3.5 w-3.5" /> Create preview key</button></div>
        {newKey && <div className="m-5 rounded-xl border border-amber-300/15 bg-amber-300/[0.035] p-5"><div className="flex items-start justify-between gap-4"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-amber-300">Copy this preview value now</p><p className="mt-2 text-[11px] leading-5 text-amber-100/60">It exists only in this browser state and is not accepted by any backend.</p></div><button type="button" aria-label="Dismiss preview secret" onClick={() => setNewKey('')} className="text-amber-100/40 hover:text-amber-100"><X className="h-4 w-4" /></button></div><div className="mt-4 flex items-center gap-2 rounded-lg border border-white/[0.07] bg-black/25 p-3"><code className="min-w-0 flex-1 truncate font-mono text-[11px] text-slate-300">{visible ? newKey : '•'.repeat(26)}</code><button type="button" aria-label={visible ? 'Hide preview key' : 'Show preview key'} onClick={() => setVisible((value) => !value)} className="rounded-md p-1.5 text-slate-600 hover:bg-white/[0.05] hover:text-white">{visible ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}</button><button type="button" aria-label="Copy preview key" onClick={copyKey} className="rounded-md p-1.5 text-slate-600 hover:bg-white/[0.05] hover:text-white">{copied ? <Check className="h-3.5 w-3.5 text-emerald-300" /> : <Copy className="h-3.5 w-3.5" />}</button></div></div>}
        {keys.length ? <div className="divide-y divide-white/[0.05]">{keys.map((key) => <div key={key.id} className="grid gap-4 p-5 sm:grid-cols-[minmax(0,1fr)_120px_100px_auto] sm:items-center"><div className="flex items-center gap-3"><span className="flex h-9 w-9 items-center justify-center rounded-lg border border-violet-300/15 bg-violet-300/[0.04] text-violet-300"><KeyRound className="h-4 w-4" /></span><div><p className="text-xs font-medium text-slate-300">{key.name}</p><p className="mt-1 font-mono text-[9px] text-slate-700">{key.prefix}</p></div></div><div><p className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Created</p><p className="mt-1 text-[10px] text-slate-500">{key.created}</p></div><div><p className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Last used</p><p className="mt-1 text-[10px] text-slate-500">{key.lastUsed}</p></div><button type="button" aria-label="Revoke preview key" onClick={() => { setKeys([]); setNewKey(''); }} className="rounded-lg border border-white/[0.07] p-2 text-slate-700 hover:border-rose-300/20 hover:text-rose-300"><Trash2 className="h-3.5 w-3.5" /></button></div>)}</div> : <div className="flex min-h-64 flex-col items-center justify-center p-8 text-center"><KeyRound className="h-6 w-6 text-slate-800" /><p className="mt-4 text-sm font-medium text-slate-400">No API keys</p><p className="mt-2 max-w-sm text-[11px] leading-5 text-slate-600">Create a local preview key to test the frontend flow. Nothing is persisted or authenticated.</p></div>}
      </section>
      <aside className="space-y-4"><div className="rounded-xl border border-emerald-300/15 bg-emerald-300/[0.025] p-5"><ShieldCheck className="h-5 w-5 text-emerald-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Providers never see reusable customer keys</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">The gateway authenticates, checks quota and balance, routes requests, meters usage, and forwards only short-lived authenticated work.</p></div><div className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><LockKeyhole className="h-5 w-5 text-violet-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Planned key controls</h3><ul className="mt-3 space-y-2 text-[11px] text-slate-600">{['Hash secrets at rest', 'Prefix-based lookup', 'Per-key scopes and quotas', 'Immediate revocation', 'Audit every lifecycle event'].map((item) => <li key={item} className="flex items-center gap-2"><span className="h-1 w-1 rounded-full bg-violet-300" />{item}</li>)}</ul></div></aside>
    </div>
  );
};

const UsageTab = () => (
  <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
    <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6"><div className="flex items-start justify-between"><div><h2 className="text-sm font-medium text-slate-200">Inference usage</h2><p className="mt-1 text-[11px] text-slate-600">Illustrative chart only · no requests have been sent</p></div><span className="rounded-full border border-white/[0.07] px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Last 7 days</span></div><div className="mt-8 flex h-56 items-end gap-3 border-b border-l border-white/[0.06] px-4 pb-4">{[8, 14, 10, 18, 12, 20, 16].map((height, index) => <div key={index} className="flex h-full flex-1 items-end"><div style={{ height: `${height}%` }} className="w-full rounded-t-xs bg-linear-to-t from-violet-400/10 to-violet-300/40" /></div>)}</div><div className="mt-4 flex items-center justify-between font-mono text-[8px] uppercase tracking-[0.16em] text-slate-800"><span>7 days ago</span><span>Today</span></div></section>
    <aside className="space-y-4">{[['Billable requests', '0'], ['Input tokens', '0'], ['Output tokens', '0'], ['Sandbox spend', '$0.00']].map(([label, value]) => <div key={label} className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><p className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">{label}</p><p className="mt-3 text-2xl font-medium text-slate-200">{value}</p></div>)}</aside>
  </div>
);

const DocsTab = ({ selectedModel }) => {
  const [copied, setCopied] = useState(false);
  const copy = async () => { await navigator.clipboard?.writeText(CODE_SAMPLE); setCopied(true); window.setTimeout(() => setCopied(false), 1400); };
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_330px]">
      <section className="rounded-xl border border-white/[0.07] bg-[#0b0d14] p-5 sm:p-6"><div className="flex items-center justify-between"><div><h2 className="text-sm font-medium text-slate-200">OpenAI-compatible JavaScript</h2><p className="mt-1 text-[11px] text-slate-600">Planned gateway contract · hostname is intentionally non-routable</p></div><button type="button" onClick={copy} className="flex items-center gap-2 rounded-lg border border-white/[0.07] px-3 py-2 text-[10px] text-slate-500 hover:text-white">{copied ? <Check className="h-3.5 w-3.5 text-emerald-300" /> : <Clipboard className="h-3.5 w-3.5" />}{copied ? 'Copied' : 'Copy'}</button></div><pre className="mt-5 overflow-x-auto rounded-lg border border-white/[0.06] bg-black/30 p-5 font-mono text-[11px] leading-6 text-slate-400"><code>{CODE_SAMPLE.replace('preview/chat-8b', selectedModel.id)}</code></pre></section>
      <aside className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.025] p-5"><Zap className="h-5 w-5 text-cyan-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Gateway responsibilities</h3><ul className="mt-4 space-y-3 text-[11px] leading-5 text-slate-600">{['Authenticate the marketplace key', 'Check scopes, quota, and balance', 'Route only to healthy deployments', 'Meter requests, tokens, and GPU time', 'Apply rate limits and failover', 'Keep reusable credentials away from providers'].map((item) => <li key={item} className="flex gap-2"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-cyan-300" />{item}</li>)}</ul></aside>
    </div>
  );
};

const ModelApiPage = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState('catalog');
  const [selectedModel, setSelectedModel] = useState(MODELS[0]);

  return (
    <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
      <button type="button" onClick={() => onNavigate('/app')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> Marketplace overview</button>
      <section className="relative mt-6 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0c0e16] p-7 sm:p-9">
        <div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-violet-400/[0.1] blur-[90px]" />
        <div className="relative grid gap-8 lg:grid-cols-[minmax(0,1fr)_330px] lg:items-end"><div><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-violet-300/15 bg-violet-300/[0.04] text-violet-300"><BrainCircuit className="h-5 w-5" /></span><p className="mt-6 font-mono text-[9px] uppercase tracking-[0.22em] text-violet-300">Managed inference product preview</p><h1 className="mt-3 max-w-3xl text-3xl font-medium tracking-[-0.04em] text-slate-100 sm:text-5xl">One API for reviewed open models</h1><p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">Explore the planned model catalog, API-key lifecycle, usage views, and OpenAI-compatible gateway without implying that inference is live.</p></div><div className="rounded-xl border border-amber-300/15 bg-amber-300/[0.035] p-4"><div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.18em] text-amber-300"><Clock3 className="h-3.5 w-3.5" /> Planning preview</div><p className="mt-2 text-[11px] leading-5 text-amber-100/60">No deployment, endpoint, key, request, token, or charge is real. Backend contracts remain the source of truth.</p></div></div>
      </section>

      <div id="model-tabs" className="mt-6 overflow-x-auto border-b border-white/[0.06]"><div className="flex min-w-max gap-1">{TABS.map((tab) => <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 border-b px-4 py-3 text-[11px] font-medium transition-colors ${activeTab === tab.id ? 'border-violet-300 text-slate-100' : 'border-transparent text-slate-600 hover:text-slate-300'}`}><tab.icon className="h-3.5 w-3.5" />{tab.label}</button>)}</div></div>
      <div className="mt-6">
        {activeTab === 'catalog' && <CatalogTab selectedModel={selectedModel} onSelectModel={setSelectedModel} />}
        {activeTab === 'keys' && <ApiKeysTab />}
        {activeTab === 'usage' && <UsageTab />}
        {activeTab === 'docs' && <DocsTab selectedModel={selectedModel} />}
      </div>
    </div>
  );
};

export default ModelApiPage;
