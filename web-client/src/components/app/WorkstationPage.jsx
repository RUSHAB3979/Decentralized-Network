import React, { useMemo, useState } from 'react';
import {
  ArrowLeft,
  Check,
  ChevronRight,
  Clock3,
  Cpu,
  Database,
  HardDrive,
  MonitorPlay,
  MonitorUp,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TimerReset,
  Wifi,
} from 'lucide-react';

const PROFILES = [
  {
    id: 'creator-16',
    name: 'Creator 16',
    gpu: '16 GB GPU profile',
    cpu: '8 vCPU',
    memory: '32 GB RAM',
    storage: '100 GB ephemeral',
    apps: ['Blender', 'DaVinci Resolve', 'Unreal Engine'],
    rate: 0.34,
    bestFor: 'Medium scenes, 1080p editing, and general creative work',
    status: 'Planned profile',
  },
  {
    id: 'creator-24',
    name: 'Creator 24',
    gpu: '24 GB GPU profile',
    cpu: '16 vCPU',
    memory: '64 GB RAM',
    storage: '250 GB ephemeral',
    apps: ['Blender', 'DaVinci Resolve', 'Unreal Engine'],
    rate: 0.58,
    bestFor: 'Heavy Cycles scenes, 4K timelines, and Unreal projects',
    status: 'Planned profile',
  },
  {
    id: 'studio-48',
    name: 'Studio 48',
    gpu: '48 GB GPU profile',
    cpu: '24 vCPU',
    memory: '128 GB RAM',
    storage: '500 GB ephemeral',
    apps: ['Blender', 'Unreal Engine', 'Custom approved image'],
    rate: 1.18,
    bestFor: 'Large scenes, virtual production, and high-memory workflows',
    status: 'Future profile',
  },
];

const REGIONS = [
  { id: 'auto', name: 'Auto · best eligible', latency: 'Measured at launch' },
  { id: 'india', name: 'India', latency: 'Regional preference' },
  { id: 'apac', name: 'Asia Pacific', latency: 'Regional preference' },
];

const ProfileCard = ({ profile, selected, onSelect }) => (
  <button type="button" onClick={() => onSelect(profile)} className={`w-full rounded-xl border p-5 text-left transition-all ${selected ? 'border-amber-300/30 bg-amber-300/[0.045]' : 'border-white/[0.07] bg-white/[0.018] hover:border-white/[0.14] hover:bg-white/[0.03]'}`}>
    <div className="flex items-start justify-between gap-4"><span className="flex h-10 w-10 items-center justify-center rounded-xl border border-amber-300/15 bg-amber-300/[0.04] text-amber-300"><MonitorUp className="h-[18px] w-[18px]" /></span><span className="rounded-full border border-white/[0.07] px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.16em] text-slate-600">{profile.status}</span></div>
    <h3 className="mt-5 text-lg font-medium tracking-[-0.02em] text-slate-200">{profile.name}</h3><p className="mt-2 font-mono text-[10px] text-amber-200">{profile.gpu}</p><p className="mt-4 text-[11px] leading-5 text-slate-600">{profile.bestFor}</p>
    <div className="mt-5 grid grid-cols-2 gap-2 border-t border-white/[0.05] pt-4 text-[10px] text-slate-600"><span className="flex items-center gap-1.5"><Cpu className="h-3 w-3" />{profile.cpu}</span><span className="flex items-center gap-1.5"><Database className="h-3 w-3" />{profile.memory}</span><span className="flex items-center gap-1.5"><HardDrive className="h-3 w-3" />{profile.storage}</span><span className="text-right font-mono text-slate-400">${profile.rate.toFixed(2)}/hr preview</span></div>
  </button>
);

const SessionReady = ({ profile, app, duration, onReset, onNavigate }) => (
  <section className="mx-auto max-w-4xl rounded-2xl border border-emerald-300/20 bg-emerald-300/[0.035] p-8 sm:p-10">
    <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-300/[0.06] text-emerald-300"><Check className="h-5 w-5" /></span><p className="mt-7 font-mono text-[9px] uppercase tracking-[0.22em] text-emerald-300">Frontend flow complete</p><h1 className="mt-3 max-w-3xl text-3xl font-medium tracking-[-0.04em] text-slate-100 sm:text-5xl">Your workstation request is ready for backend design.</h1><p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">No capacity was reserved and no stream was opened. This state verifies the profile, application, region, duration, quote, and confirmation experience.</p>
    <div className="mt-8 grid gap-4 rounded-xl border border-white/[0.07] bg-black/20 p-5 sm:grid-cols-3">{[['Profile', profile.name], ['Application', app], ['Reservation', `${duration} hour${duration === 1 ? '' : 's'}`]].map(([label, value]) => <div key={label}><p className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-700">{label}</p><p className="mt-2 text-xs font-medium text-slate-200">{value}</p></div>)}</div>
    <div className="mt-7 flex flex-wrap gap-3"><button type="button" onClick={onReset} className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]"><RotateCcw className="h-3.5 w-3.5" /> Configure another</button><button type="button" onClick={() => onNavigate('/app')} className="rounded-lg border border-white/[0.08] bg-white/[0.02] px-5 py-3 text-xs font-medium text-slate-400 hover:text-white">Return to marketplace</button></div>
  </section>
);

const WorkstationPage = ({ onNavigate }) => {
  const [profile, setProfile] = useState(PROFILES[0]);
  const [application, setApplication] = useState('Blender');
  const [region, setRegion] = useState('auto');
  const [duration, setDuration] = useState(1);
  const [storage, setStorage] = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const quote = useMemo(() => {
    const compute = profile.rate * duration;
    const projectStorage = storage ? 0.04 * duration : 0;
    return { compute, projectStorage, total: compute + projectStorage };
  }, [duration, profile, storage]);

  if (confirmed) return <div className="mx-auto max-w-[1480px] px-4 py-10 sm:px-7 lg:px-9 lg:py-16"><SessionReady profile={profile} app={application} duration={duration} onReset={() => setConfirmed(false)} onNavigate={onNavigate} /></div>;

  return (
    <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
      <button type="button" onClick={() => onNavigate('/app')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> Marketplace overview</button>
      <section className="relative mt-6 overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0c0e16] p-7 sm:p-9"><div className="pointer-events-none absolute -right-20 -top-24 h-64 w-64 rounded-full bg-amber-400/[0.1] blur-[90px]" /><div className="relative grid gap-8 lg:grid-cols-[minmax(0,1fr)_330px] lg:items-end"><div><span className="flex h-11 w-11 items-center justify-center rounded-xl border border-amber-300/15 bg-amber-300/[0.04] text-amber-300"><MonitorPlay className="h-5 w-5" /></span><p className="mt-6 font-mono text-[9px] uppercase tracking-[0.22em] text-amber-300">Interactive compute preview</p><h1 className="mt-3 max-w-3xl text-3xl font-medium tracking-[-0.04em] text-slate-100 sm:text-5xl">A clean GPU workstation for the hours you need</h1><p className="mt-5 max-w-3xl text-sm leading-7 text-slate-400">Choose intent and duration while the planned scheduler selects verified hardware, establishes short-lived streaming credentials, mounts scoped project storage, and proves teardown.</p></div><div className="rounded-xl border border-amber-300/15 bg-amber-300/[0.035] p-4"><div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.18em] text-amber-300"><Clock3 className="h-3.5 w-3.5" /> Planning preview</div><p className="mt-2 text-[11px] leading-5 text-amber-100/60">No GPU availability, application license, region, stream, or price is represented as live.</p></div></div></section>

      <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-6">
          <section><div className="flex items-end justify-between gap-4"><div><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-700">01 · Hardware intent</p><h2 className="mt-2 text-lg font-medium text-slate-200">Choose a workstation profile</h2></div><span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Exact GPU selected later</span></div><div className="mt-4 grid gap-4 lg:grid-cols-3">{PROFILES.map((candidate) => <ProfileCard key={candidate.id} profile={candidate} selected={candidate.id === profile.id} onSelect={setProfile} />)}</div></section>

          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6"><p className="font-mono text-[9px] uppercase tracking-[0.2em] text-slate-700">02 · Session intent</p><h2 className="mt-2 text-lg font-medium text-slate-200">Configure the reservation</h2><div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="block"><span className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Application</span><select value={application} onChange={(event) => setApplication(event.target.value)} className="mt-2 h-11 w-full rounded-lg border border-white/[0.08] bg-[#0b0d14] px-3 text-xs text-slate-300 outline-hidden focus:border-amber-300/30">{profile.apps.map((app) => <option key={app}>{app}</option>)}</select></label>
            <label className="block"><span className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Region preference</span><select value={region} onChange={(event) => setRegion(event.target.value)} className="mt-2 h-11 w-full rounded-lg border border-white/[0.08] bg-[#0b0d14] px-3 text-xs text-slate-300 outline-hidden focus:border-amber-300/30">{REGIONS.map((option) => <option key={option.id} value={option.id}>{option.name}</option>)}</select></label>
            <label className="block"><span className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Reservation duration</span><select value={duration} onChange={(event) => setDuration(Number(event.target.value))} className="mt-2 h-11 w-full rounded-lg border border-white/[0.08] bg-[#0b0d14] px-3 text-xs text-slate-300 outline-hidden focus:border-amber-300/30">{[1, 2, 4, 8].map((hours) => <option key={hours} value={hours}>{hours} hour{hours === 1 ? '' : 's'}</option>)}</select></label>
            <label className="flex min-h-11 cursor-pointer items-center gap-3 self-end rounded-lg border border-white/[0.08] bg-[#0b0d14] px-4"><input type="checkbox" checked={storage} onChange={(event) => setStorage(event.target.checked)} className="accent-amber-300" /><span><span className="block text-xs text-slate-300">Attach project storage</span><span className="mt-0.5 block text-[9px] text-slate-700">Preview add-on · $0.04/hr</span></span></label>
          </div></section>

          <section className="grid gap-4 md:grid-cols-3">{[
            [Wifi, 'Measured path', 'Latency and packet loss must pass profile-specific launch thresholds.'],
            [ShieldCheck, 'Short-lived access', 'The browser receives session-scoped credentials, never provider credentials.'],
            [TimerReset, 'Verified teardown', 'Session storage and credentials must be destroyed before the node returns to inventory.'],
          ].map(([Icon, title, body]) => <article key={title} className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5"><Icon className="h-5 w-5 text-amber-300" /><h3 className="mt-4 text-sm font-medium text-slate-200">{title}</h3><p className="mt-2 text-[11px] leading-5 text-slate-600">{body}</p></article>)}</section>
        </div>

        <aside className="h-fit rounded-xl border border-white/[0.08] bg-[#0d0f17] p-5 xl:sticky xl:top-[96px]"><div className="flex items-center justify-between"><h2 className="text-sm font-medium text-slate-200">Session preview</h2><Sparkles className="h-4 w-4 text-amber-300" /></div><div className="mt-5 space-y-3 border-y border-white/[0.06] py-5 text-[11px]">{[['Profile', profile.name], ['GPU intent', profile.gpu], ['Application', application], ['Region', REGIONS.find((item) => item.id === region)?.name], ['Duration', `${duration} hour${duration === 1 ? '' : 's'}`]].map(([label, value]) => <div key={label} className="flex items-start justify-between gap-4"><span className="text-slate-700">{label}</span><span className="text-right text-slate-400">{value}</span></div>)}</div><div className="mt-5 space-y-2 text-[11px]"><div className="flex justify-between"><span className="text-slate-700">Compute preview</span><span className="text-slate-400">${quote.compute.toFixed(2)}</span></div><div className="flex justify-between"><span className="text-slate-700">Project storage</span><span className="text-slate-400">${quote.projectStorage.toFixed(2)}</span></div></div><div className="mt-5 border-t border-white/[0.06] pt-5"><div className="flex items-end justify-between"><div><p className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Illustrative total</p><p className="mt-2 text-3xl font-medium tracking-[-0.04em] text-slate-100">${quote.total.toFixed(2)}</p></div><span className="font-mono text-[8px] uppercase tracking-[0.16em] text-amber-300">Not a live quote</span></div><button type="button" onClick={() => { setConfirmed(true); window.scrollTo({ top: 0, behavior: 'smooth' }); }} className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-100 py-3 text-xs font-semibold text-[#08090a]">Review preview session <ChevronRight className="h-3.5 w-3.5" /></button><p className="mt-3 text-center text-[9px] leading-4 text-slate-700">No reservation, stream, license, or charge is created.</p></div></aside>
      </div>
    </div>
  );
};

export default WorkstationPage;
