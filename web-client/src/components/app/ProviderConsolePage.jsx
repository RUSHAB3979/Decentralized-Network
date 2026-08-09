import React, { useState } from 'react';
import {
  Activity,
  ArrowLeft,
  BadgeCheck,
  Check,
  CircleDollarSign,
  ClipboardCheck,
  Clock3,
  Cpu,
  FileCheck2,
  Gauge,
  HeartPulse,
  KeyRound,
  Landmark,
  Network,
  Play,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  WalletCards,
  Wrench,
} from 'lucide-react';
import NodeTelemetry from '../NodeTelemetry';

const TABS = [
  { id: 'overview', label: 'Overview', icon: Gauge },
  { id: 'nodes', label: 'Simulated nodes', icon: Server },
  { id: 'onboarding', label: 'Onboarding', icon: ClipboardCheck },
  { id: 'earnings', label: 'Earnings', icon: WalletCards },
];

const OverviewTab = ({ onOpenNodes, onOpenOnboarding }) => (
  <div className="space-y-5">
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{[
      [Server, 'Simulated nodes', '3', 'Demo telemetry records'],
      [Activity, 'Schedulable capacity', '0', 'No provider connected'],
      [CircleDollarSign, 'Preview earnings', '$0.00', 'No billable workloads'],
      [HeartPulse, 'Control-plane status', 'Offline', 'Frontend sandbox only'],
    ].map(([Icon, label, value, detail]) => <article key={label} className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><div className="flex items-center justify-between"><Icon className="h-4 w-4 text-emerald-300" /><span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Preview</span></div><p className="mt-5 font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">{label}</p><p className="mt-2 text-2xl font-medium tracking-[-0.03em] text-slate-200">{value}</p><p className="mt-2 text-[10px] text-slate-700">{detail}</p></article>)}</div>
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]"><section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6"><div className="flex items-center justify-between"><div><h2 className="text-sm font-medium text-slate-200">Provider readiness</h2><p className="mt-1 text-[11px] text-slate-600">Real capacity must pass identity, benchmark, policy, and runtime gates.</p></div><BadgeCheck className="h-5 w-5 text-emerald-300" /></div><div className="mt-6 space-y-3">{[
      ['Identity and payout verification', 'Required before any earnings accrue', false],
      ['Cryptographic agent enrollment', 'Short-lived credentials and signed heartbeats', false],
      ['Hardware benchmark', 'Verified GPU, VRAM, thermal, power, and stability record', false],
      ['Runtime policy acceptance', 'Provider chooses approved workload classes', false],
    ].map(([title, detail, complete]) => <div key={title} className="flex items-start gap-3 rounded-lg border border-white/[0.06] bg-[#0b0d14] p-4"><span className={`mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border ${complete ? 'border-emerald-300/30 bg-emerald-300/[0.08] text-emerald-300' : 'border-white/[0.1] text-slate-700'}`}>{complete ? <Check className="h-3 w-3" /> : <span className="h-1.5 w-1.5 rounded-full bg-slate-700" />}</span><div><p className="text-xs font-medium text-slate-300">{title}</p><p className="mt-1 text-[10px] leading-5 text-slate-600">{detail}</p></div></div>)}</div><button type="button" onClick={onOpenOnboarding} className="mt-5 inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]">Open onboarding preview <Play className="h-3.5 w-3.5" /></button></section>
      <aside className="space-y-4"><div className="rounded-xl border border-emerald-300/15 bg-emerald-300/[0.025] p-5"><ShieldCheck className="h-5 w-5 text-emerald-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Provider control stays explicit</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">Providers opt into workload classes, availability windows, price policies, resource limits, and maintenance mode.</p></div><button type="button" onClick={onOpenNodes} className="flex w-full items-center justify-between rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 text-left"><span><span className="block text-sm font-medium text-slate-300">Inspect telemetry layout</span><span className="mt-1 block text-[10px] text-slate-600">Three simulated hardware records</span></span><Network className="h-5 w-5 text-cyan-300" /></button></aside></div>
  </div>
);

const OnboardingTab = () => {
  const [accepted, setAccepted] = useState(false);
  const [step, setStep] = useState(0);
  const steps = [
    { icon: FileCheck2, title: 'Provider identity', body: 'Verify the operator, payout destination, agreements, tax requirements, and supported region.' },
    { icon: KeyRound, title: 'Agent enrollment', body: 'Install the signed provider agent and exchange enrollment material for a short-lived node identity.' },
    { icon: Cpu, title: 'Hardware benchmark', body: 'Collect GPU identity, VRAM, drivers, encoder support, thermals, stability, and verified performance.' },
    { icon: SlidersHorizontal, title: 'Offer policy', body: 'Choose workload classes, availability, prices, hard resource limits, maintenance behavior, and region disclosure.' },
  ];
  const selected = steps[step];
  const Icon = selected.icon;
  return (
    <div className="grid gap-5 xl:grid-cols-[320px_minmax(0,1fr)]"><nav className="space-y-2">{steps.map((item, index) => <button key={item.title} type="button" onClick={() => setStep(index)} className={`flex w-full items-center gap-3 rounded-xl border p-4 text-left ${step === index ? 'border-emerald-300/25 bg-emerald-300/[0.04]' : 'border-white/[0.07] bg-white/[0.018] hover:bg-white/[0.03]'}`}><span className={`flex h-8 w-8 items-center justify-center rounded-lg border ${step === index ? 'border-emerald-300/20 text-emerald-300' : 'border-white/[0.07] text-slate-700'}`}>{String(index + 1).padStart(2, '0')}</span><span><span className="block text-xs font-medium text-slate-300">{item.title}</span><span className="mt-1 block font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Not started</span></span></button>)}</nav><section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-6 sm:p-8"><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-300/15 bg-emerald-300/[0.04] text-emerald-300"><Icon className="h-5 w-5" /></span><p className="mt-6 font-mono text-[9px] uppercase tracking-[0.2em] text-emerald-300">Step {step + 1} of {steps.length}</p><h2 className="mt-2 text-2xl font-medium tracking-[-0.03em] text-slate-100">{selected.title}</h2><p className="mt-4 max-w-2xl text-sm leading-7 text-slate-500">{selected.body}</p><div className="mt-6 rounded-xl border border-amber-300/15 bg-amber-300/[0.025] p-4 text-[11px] leading-5 text-amber-100/60">This frontend does not collect identity documents, keys, payout information, or hardware data. Real onboarding requires approved backend contracts and secure handling.</div>{step === steps.length - 1 && <label className="mt-5 flex cursor-pointer items-start gap-3 rounded-xl border border-white/[0.07] bg-[#0b0d14] p-4"><input type="checkbox" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} className="mt-0.5 accent-emerald-300" /><span><span className="block text-xs font-medium text-slate-300">Preview provider policy acknowledgement</span><span className="mt-1 block text-[10px] text-slate-600">Local UI state only; this is not a legal acceptance.</span></span></label>}<div className="mt-6 flex gap-3"><button type="button" disabled={step === 0} onClick={() => setStep((value) => Math.max(0, value - 1))} className="rounded-lg border border-white/[0.08] px-5 py-3 text-xs text-slate-500 disabled:opacity-30">Previous</button><button type="button" disabled={step === steps.length - 1 && !accepted} onClick={() => setStep((value) => Math.min(steps.length - 1, value + 1))} className="rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a] disabled:cursor-not-allowed disabled:opacity-35">{step === steps.length - 1 ? 'Preview complete' : 'Continue'}</button></div></section></div>
  );
};

const EarningsTab = () => (
  <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]"><section className="rounded-xl border border-white/[0.07] bg-white/[0.018]"><div className="grid gap-px bg-white/[0.05] sm:grid-cols-3">{[['Pending', '$0.00'], ['Available', '$0.00'], ['Lifetime preview', '$0.00']].map(([label, value]) => <div key={label} className="bg-[#090a10] p-6"><p className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-700">{label}</p><p className="mt-3 text-2xl font-medium text-slate-200">{value}</p></div>)}</div><div className="flex min-h-60 flex-col items-center justify-center p-8 text-center"><CircleDollarSign className="h-6 w-6 text-slate-800" /><p className="mt-4 text-sm font-medium text-slate-400">No provider earnings</p><p className="mt-2 max-w-md text-[11px] leading-5 text-slate-600">Earnings require independently reconciled usage and release only after the verification and dispute window.</p></div></section><aside className="space-y-4"><div className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><Landmark className="h-5 w-5 text-violet-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Payout account</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">Not connected. Provider KYC, payout verification, fees, taxes, and regional requirements need legal and payment-provider review.</p></div><div className="rounded-xl border border-cyan-300/15 bg-cyan-300/[0.025] p-5"><Wrench className="h-5 w-5 text-cyan-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Earnings evidence</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">Every line item should link to workload, attempt, verified usage, platform fee, adjustment, dispute status, and payout event.</p></div></aside></div>
);

const ProviderConsolePage = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState('overview');
  return (
    <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10"><button type="button" onClick={() => onNavigate('/app')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> Marketplace overview</button><section className="relative mt-6 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0c0e16] p-7 sm:p-9"><div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-emerald-400/[0.09] blur-[90px]" /><div className="relative grid gap-8 lg:grid-cols-[minmax(0,1fr)_330px] lg:items-end"><div><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-300/15 bg-emerald-300/[0.04] text-emerald-300"><Server className="h-5 w-5" /></span><p className="mt-6 font-mono text-[9px] uppercase tracking-[0.22em] text-emerald-300">Provider experience preview</p><h1 className="mt-3 max-w-3xl text-3xl font-medium tracking-[-0.04em] text-slate-100 sm:text-5xl">Turn controlled idle capacity into accountable supply</h1><p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">Preview node operations, onboarding gates, telemetry, workload policy, and earnings evidence without enrolling this machine or collecting sensitive information.</p></div><div className="rounded-xl border border-amber-300/15 bg-amber-300/[0.035] p-4"><div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.18em] text-amber-300"><Clock3 className="h-3.5 w-3.5" /> Simulated provider state</div><p className="mt-2 text-[11px] leading-5 text-amber-100/60">No provider identity, node, heartbeat, offer, usage, earning, or payout shown here is real.</p></div></div></section><div className="mt-6 overflow-x-auto border-b border-white/[0.06]"><div className="flex min-w-max gap-1">{TABS.map((tab) => <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 border-b px-4 py-3 text-[11px] font-medium ${activeTab === tab.id ? 'border-emerald-300 text-slate-100' : 'border-transparent text-slate-600 hover:text-slate-300'}`}><tab.icon className="h-3.5 w-3.5" />{tab.label}</button>)}</div></div><div className="mt-6">{activeTab === 'overview' && <OverviewTab onOpenNodes={() => setActiveTab('nodes')} onOpenOnboarding={() => setActiveTab('onboarding')} />}{activeTab === 'nodes' && <div className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6"><NodeTelemetry /></div>}{activeTab === 'onboarding' && <OnboardingTab />}{activeTab === 'earnings' && <EarningsTab />}</div></div>
  );
};

export default ProviderConsolePage;
