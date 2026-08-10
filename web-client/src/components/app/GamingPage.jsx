import React, { useState } from 'react';
import {
  ArrowLeft,
  BadgeAlert,
  Check,
  ChevronRight,
  Clock3,
  Gamepad2,
  KeyRound,
  MonitorPlay,
  Network,
  Radio,
  ShieldCheck,
  Signal,
  TimerReset,
  Wifi,
} from 'lucide-react';

const GATES = [
  { icon: ShieldCheck, title: 'Rights gate', body: 'A title cannot schedule without a documented commercial permission or compliant customer-owned entitlement flow.' },
  { icon: Gamepad2, title: 'Compatibility gate', body: 'Anti-cheat, DRM, controller, encoder, operating-system, and hardware behavior must be tested per title.' },
  { icon: Signal, title: 'Network gate', body: 'Measured round-trip latency, jitter, loss, upload bandwidth, and relay path must meet the selected stream target.' },
  { icon: TimerReset, title: 'Session gate', body: 'Short-lived credentials, encrypted signaling, isolated storage, usage limits, and teardown evidence are mandatory.' },
];

const STREAM_TARGETS = [
  { name: 'Responsive 1080', resolution: '1080p · 60 fps', target: '< 45 ms RTT target', codec: 'AV1 / H.265 candidate' },
  { name: 'Competitive 1440', resolution: '1440p · 120 fps', target: '< 30 ms RTT target', codec: 'AV1 candidate' },
  { name: 'Cinematic 4K', resolution: '4K · 60 fps', target: '< 55 ms RTT target', codec: 'AV1 / H.265 candidate' },
];

const ReadinessPreview = () => {
  const [region, setRegion] = useState('India');
  const [connection, setConnection] = useState('Fiber / wired');
  const [controller, setController] = useState(true);
  const [checked, setChecked] = useState(false);
  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]"><section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6"><h2 className="text-sm font-medium text-slate-200">Session-intent preview</h2><p className="mt-1 text-[11px] text-slate-600">This checks only the frontend flow; it does not measure your real connection.</p><div className="mt-6 grid gap-4 sm:grid-cols-2"><label className="block"><span className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Region preference</span><select value={region} onChange={(event) => setRegion(event.target.value)} className="mt-2 h-11 w-full rounded-lg border border-white/[0.08] bg-[#0b0d14] px-3 text-xs text-slate-300 outline-hidden focus:border-emerald-300/30"><option>India</option><option>Asia Pacific</option><option>Auto · measured path</option></select></label><label className="block"><span className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Connection type</span><select value={connection} onChange={(event) => setConnection(event.target.value)} className="mt-2 h-11 w-full rounded-lg border border-white/[0.08] bg-[#0b0d14] px-3 text-xs text-slate-300 outline-hidden focus:border-emerald-300/30"><option>Fiber / wired</option><option>Wi-Fi 6 or newer</option><option>Mobile network</option></select></label></div><label className="mt-4 flex cursor-pointer items-center gap-3 rounded-lg border border-white/[0.07] bg-[#0b0d14] p-4"><input type="checkbox" checked={controller} onChange={(event) => setController(event.target.checked)} className="accent-emerald-300" /><span><span className="block text-xs text-slate-300">Controller available</span><span className="mt-1 block text-[10px] text-slate-600">Input-device compatibility still requires real browser testing.</span></span></label><button type="button" onClick={() => setChecked(true)} className="mt-5 inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]">Preview readiness result <ChevronRight className="h-3.5 w-3.5" /></button>{checked && <div className="mt-5 rounded-xl border border-cyan-300/15 bg-cyan-300/[0.035] p-4"><div className="flex items-center gap-2 text-xs font-medium text-cyan-200"><Check className="h-4 w-4" /> Frontend intent captured</div><p className="mt-2 text-[11px] leading-5 text-slate-600">{region} · {connection} · controller {controller ? 'available' : 'not selected'}. A real launch must run active network and compatibility tests.</p></div>}</section><aside className="rounded-xl border border-amber-300/15 bg-amber-300/[0.025] p-5"><BadgeAlert className="h-5 w-5 text-amber-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">Why there is no game catalog</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">Displaying titles as rentable would imply rights and availability that do not exist. The catalog stays closed until each title passes commercial and technical review.</p><div className="mt-5 flex items-start gap-2 rounded-lg border border-white/[0.06] bg-black/20 p-3 text-[10px] leading-5 text-slate-600"><KeyRound className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" />BYOL can reduce redistribution risk, but it does not automatically satisfy publisher, DRM, anti-cheat, or cloud-use terms.</div></aside></div>
  );
};

const GamingPage = ({ onNavigate }) => (
  <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10"><button type="button" onClick={() => onNavigate('/app')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> Marketplace overview</button><section className="relative mt-6 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0c0e16] p-7 sm:p-9"><div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-emerald-400/[0.09] blur-[90px]" /><div className="relative grid gap-8 lg:grid-cols-[minmax(0,1fr)_330px] lg:items-end"><div><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-emerald-300/15 bg-emerald-300/[0.04] text-emerald-300"><Gamepad2 className="h-5 w-5" /></span><p className="mt-6 font-mono text-[9px] uppercase tracking-[0.22em] text-emerald-300">Permission-gated interactive track</p><h1 className="mt-3 max-w-3xl text-3xl font-medium tracking-[-0.04em] text-slate-100 sm:text-5xl">Cloud gaming, without pretending the rights problem is solved</h1><p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">The gaming experience can reuse interactive allocation and streaming primitives only after title rights, anti-cheat, DRM, session security, latency, and provider trust requirements pass.</p></div><div className="rounded-xl border border-amber-300/15 bg-amber-300/[0.035] p-4"><div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.18em] text-amber-300"><Clock3 className="h-3.5 w-3.5" /> Research track</div><p className="mt-2 text-[11px] leading-5 text-amber-100/60">No title, stream target, region, provider, price, or launch button is represented as commercially available.</p></div></div></section>
    <section className="mt-6"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-700">Release gates</p><h2 className="mt-2 text-lg font-medium text-slate-200">Four gates before any title appears</h2></div><div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">{GATES.map(({ icon: Icon, title, body }) => <article key={title} className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><Icon className="h-5 w-5 text-emerald-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">{title}</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">{body}</p></article>)}</div></section>
    <section className="mt-6 rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6"><div className="flex items-center justify-between"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-700">Streaming targets</p><h2 className="mt-2 text-lg font-medium text-slate-200">Experience profiles under investigation</h2></div><Radio className="h-5 w-5 text-cyan-300" /></div><div className="mt-5 grid gap-4 lg:grid-cols-3">{STREAM_TARGETS.map((target) => <article key={target.name} className="rounded-xl border border-white/[0.07] bg-[#0b0d14] p-5"><div className="flex items-center justify-between"><MonitorPlay className="h-5 w-5 text-cyan-300" /><span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Research target</span></div><h3 className="mt-5 text-sm font-medium text-slate-200">{target.name}</h3><p className="mt-2 font-mono text-[10px] text-cyan-200">{target.resolution}</p><div className="mt-4 space-y-2 border-t border-white/[0.05] pt-4 text-[10px] text-slate-600"><p className="flex items-center gap-2"><Wifi className="h-3 w-3" />{target.target}</p><p className="flex items-center gap-2"><Network className="h-3 w-3" />{target.codec}</p></div></article>)}</div></section>
    <section className="mt-6"><ReadinessPreview /></section>
  </div>
);

export default GamingPage;
