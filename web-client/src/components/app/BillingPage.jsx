import React, { useState } from 'react';
import {
  ArrowLeft,
  BellRing,
  Check,
  CircleDollarSign,
  Clock3,
  CreditCard,
  FileText,
  Gauge,
  Landmark,
  LockKeyhole,
  ReceiptText,
  Save,
  ShieldCheck,
  SlidersHorizontal,
  WalletCards,
} from 'lucide-react';

const TABS = [
  { id: 'overview', label: 'Overview', icon: WalletCards },
  { id: 'limits', label: 'Spending controls', icon: SlidersHorizontal },
  { id: 'invoices', label: 'Invoices', icon: ReceiptText },
];

const EmptyLedger = () => (
  <div className="rounded-xl border border-white/[0.07] bg-white/[0.018]">
    <div className="grid grid-cols-[1.2fr_.8fr_.8fr_.7fr] border-b border-white/[0.06] px-5 py-3 font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700"><span>Event</span><span>Workload</span><span>Amount</span><span className="text-right">Status</span></div>
    <div className="flex min-h-60 flex-col items-center justify-center p-8 text-center"><FileText className="h-6 w-6 text-slate-800" /><p className="mt-4 text-sm font-medium text-slate-400">No ledger events</p><p className="mt-2 max-w-md text-[11px] leading-5 text-slate-600">Preview jobs, keys, and sessions never create charges. Real usage must arrive as authenticated, append-only ledger events.</p></div>
  </div>
);

const OverviewTab = () => (
  <div className="space-y-5">
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">{[
      [CircleDollarSign, 'Current balance', '$0.00', 'No payment account'],
      [Gauge, 'Current period', '$0.00', 'No billable usage'],
      [Clock3, 'Reserved spend', '$0.00', 'No active workloads'],
      [Landmark, 'Provider earnings', '$0.00', 'No payout account'],
    ].map(([Icon, label, value, detail]) => <article key={label} className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><div className="flex items-center justify-between"><Icon className="h-4 w-4 text-cyan-300" /><span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Sandbox</span></div><p className="mt-5 font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">{label}</p><p className="mt-2 text-2xl font-medium tracking-[-0.03em] text-slate-200">{value}</p><p className="mt-2 text-[10px] text-slate-700">{detail}</p></article>)}</div>
    <section><div className="mb-4"><h2 className="text-sm font-medium text-slate-200">Usage ledger</h2><p className="mt-1 text-[11px] text-slate-600">Customer charges, refunds, platform fees, and provider earnings must reconcile here.</p></div><EmptyLedger /></section>
  </div>
);

const LimitsTab = () => {
  const [monthlyCap, setMonthlyCap] = useState('50.00');
  const [alertAt, setAlertAt] = useState('80');
  const [autoStop, setAutoStop] = useState(true);
  const [saved, setSaved] = useState(false);
  const save = (event) => { event.preventDefault(); setSaved(true); window.setTimeout(() => setSaved(false), 1800); };

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <form onSubmit={save} className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6"><div className="flex items-start gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl border border-cyan-300/15 bg-cyan-300/[0.04] text-cyan-300"><SlidersHorizontal className="h-[18px] w-[18px]" /></span><div><h2 className="text-sm font-medium text-slate-200">Account spending controls</h2><p className="mt-1 text-[11px] leading-5 text-slate-600">This frontend state is not persisted. The real backend must enforce every cap independently.</p></div></div><div className="mt-6 grid gap-4 sm:grid-cols-2"><label className="block"><span className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Monthly hard cap</span><div className="relative mt-2"><span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-600">$</span><input type="number" min="0" step="0.01" value={monthlyCap} onChange={(event) => setMonthlyCap(event.target.value)} className="h-11 w-full rounded-lg border border-white/[0.08] bg-[#0b0d14] pl-7 pr-3 text-xs text-slate-300 outline-none focus:border-cyan-300/30" /></div></label><label className="block"><span className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Alert threshold</span><div className="relative mt-2"><input type="number" min="1" max="100" value={alertAt} onChange={(event) => setAlertAt(event.target.value)} className="h-11 w-full rounded-lg border border-white/[0.08] bg-[#0b0d14] px-3 pr-8 text-xs text-slate-300 outline-none focus:border-cyan-300/30" /><span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-slate-600">%</span></div></label></div><label className="mt-5 flex cursor-pointer items-start gap-3 rounded-xl border border-white/[0.07] bg-[#0b0d14] p-4"><input type="checkbox" checked={autoStop} onChange={(event) => setAutoStop(event.target.checked)} className="mt-0.5 accent-cyan-300" /><span><span className="block text-xs font-medium text-slate-300">Stop new workload placement at the hard cap</span><span className="mt-1 block text-[10px] leading-5 text-slate-600">Existing workloads need explicit per-workload stop and approval behavior; an account cap alone is not enough.</span></span></label><button type="submit" className="mt-5 inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]">{saved ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Save className="h-3.5 w-3.5" />}{saved ? 'Preview settings saved locally' : 'Save preview settings'}</button></form>
      <aside className="space-y-4"><div className="rounded-xl border border-amber-300/15 bg-amber-300/[0.025] p-5"><BellRing className="h-5 w-5 text-amber-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Alerts are not enforcement</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">Notifications can fail or arrive late. Quotes, leases, gateway requests, and sessions must check authoritative spending state.</p></div><div className="rounded-xl border border-emerald-300/15 bg-emerald-300/[0.025] p-5"><ShieldCheck className="h-5 w-5 text-emerald-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Required billing invariants</h3><ul className="mt-3 space-y-2 text-[11px] text-slate-600">{['Immutable ledger events', 'Idempotent usage reconciliation', 'Quote expiry and hard maximum', 'Bounded failure charges', 'Automatic platform-failure credits'].map((item) => <li key={item} className="flex items-center gap-2"><span className="h-1 w-1 rounded-full bg-emerald-300" />{item}</li>)}</ul></div></aside>
    </div>
  );
};

const InvoicesTab = () => (
  <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]"><section className="rounded-xl border border-white/[0.07] bg-white/[0.018]"><div className="border-b border-white/[0.06] p-5"><h2 className="text-sm font-medium text-slate-200">Invoices and receipts</h2><p className="mt-1 text-[11px] text-slate-600">Generated only from reconciled ledger events after a licensed payment provider is connected.</p></div><div className="flex min-h-64 flex-col items-center justify-center p-8 text-center"><ReceiptText className="h-6 w-6 text-slate-800" /><p className="mt-4 text-sm font-medium text-slate-400">No invoices</p><p className="mt-2 text-[11px] text-slate-600">The frontend sandbox cannot create financial records.</p></div></section><aside className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><CreditCard className="h-5 w-5 text-violet-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Payment method</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">Not connected. NodeForge should use a licensed payment provider rather than implementing an unregulated stored-value wallet.</p><div className="mt-5 flex items-center gap-2 rounded-lg border border-white/[0.06] bg-black/20 p-3 text-[10px] text-slate-700"><LockKeyhole className="h-3.5 w-3.5" /> No card data is collected</div></aside></div>
);

const BillingPage = ({ onNavigate }) => {
  const [activeTab, setActiveTab] = useState('overview');
  return (
    <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
      <button type="button" onClick={() => onNavigate('/app')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> Marketplace overview</button>
      <section className="relative mt-6 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0c0e16] p-7 sm:p-9"><div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-cyan-400/[0.08] blur-[90px]" /><div className="relative grid gap-8 lg:grid-cols-[minmax(0,1fr)_330px] lg:items-end"><div><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-cyan-300/15 bg-cyan-300/[0.04] text-cyan-300"><WalletCards className="h-5 w-5" /></span><p className="mt-6 font-mono text-[9px] uppercase tracking-[0.22em] text-cyan-300">Usage and billing preview</p><h1 className="mt-3 max-w-3xl text-3xl font-medium tracking-[-0.04em] text-slate-100 sm:text-5xl">Every GPU-second should be explainable</h1><p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">Preview account controls and the future ledger surface without presenting mock jobs as real usage or pretending to hold customer funds.</p></div><div className="rounded-xl border border-amber-300/15 bg-amber-300/[0.035] p-4"><div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.18em] text-amber-300"><Clock3 className="h-3.5 w-3.5" /> No payment connection</div><p className="mt-2 text-[11px] leading-5 text-amber-100/60">All displayed balances, controls, invoices, charges, and earnings are local preview state.</p></div></div></section>
      <div className="mt-6 overflow-x-auto border-b border-white/[0.06]"><div className="flex min-w-max gap-1">{TABS.map((tab) => <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)} className={`flex items-center gap-2 border-b px-4 py-3 text-[11px] font-medium ${activeTab === tab.id ? 'border-cyan-300 text-slate-100' : 'border-transparent text-slate-600 hover:text-slate-300'}`}><tab.icon className="h-3.5 w-3.5" />{tab.label}</button>)}</div></div><div className="mt-6">{activeTab === 'overview' && <OverviewTab />}{activeTab === 'limits' && <LimitsTab />}{activeTab === 'invoices' && <InvoicesTab />}</div>
    </div>
  );
};

export default BillingPage;
