import React, { useMemo, useState } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clapperboard,
  Cpu,
  FileArchive,
  Film,
  HardDriveUpload,
  Info,
  RotateCcw,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';

const GPU_PROFILES = [
  { id: 'balanced', label: 'Balanced', gpu: '12–16 GB VRAM', previewRate: 0.18, speed: 1 },
  { id: 'performance', label: 'Performance', gpu: '20–24 GB VRAM', previewRate: 0.38, speed: 1.8 },
  { id: 'maximum', label: 'Maximum', gpu: '40+ GB VRAM', previewRate: 0.72, speed: 3 },
];

const RenderJobPage = ({ onNavigate }) => {
  const [file, setFile] = useState(null);
  const [engine, setEngine] = useState('cycles');
  const [version, setVersion] = useState('4.3');
  const [gpuProfile, setGpuProfile] = useState('balanced');
  const [region, setRegion] = useState('auto');
  const [frameStart, setFrameStart] = useState(1);
  const [frameEnd, setFrameEnd] = useState(120);
  const [output, setOutput] = useState('png');
  const [spendingLimit, setSpendingLimit] = useState('5.00');
  const [submitted, setSubmitted] = useState(false);

  const quote = useMemo(() => {
    const profile = GPU_PROFILES.find((item) => item.id === gpuProfile) || GPU_PROFILES[0];
    const start = Number(frameStart) || 1;
    const end = Number(frameEnd) || start;
    const frameCount = Math.max(1, end - start + 1);
    const estimatedMinutes = Math.max(4, Math.ceil((frameCount * 1.7) / profile.speed));
    const estimatedCost = ((estimatedMinutes / 60) * profile.previewRate).toFixed(2);
    return { profile, frameCount, estimatedMinutes, estimatedCost };
  }, [frameStart, frameEnd, gpuProfile]);

  const submit = (event) => {
    event.preventDefault();
    if (!file) return;
    setSubmitted(true);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const reset = () => {
    setSubmitted(false);
    setFile(null);
    setFrameStart(1);
    setFrameEnd(120);
  };

  if (submitted) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-10 sm:px-7 lg:py-16">
        <div className="relative overflow-hidden rounded-2xl border border-emerald-300/15 bg-[#0c0f14] p-7 sm:p-10">
          <div className="pointer-events-none absolute right-0 top-0 h-72 w-72 rounded-full bg-emerald-400/[0.08] blur-[100px]" />
          <div className="relative">
            <span className="flex h-12 w-12 items-center justify-center rounded-xl border border-emerald-300/20 bg-emerald-300/[0.06] text-emerald-300">
              <CheckCircle2 className="h-6 w-6" />
            </span>
            <p className="mt-6 font-mono text-[9px] uppercase tracking-[0.24em] text-emerald-300">Frontend flow complete</p>
            <h1 className="mt-3 text-3xl font-medium tracking-[-0.035em] text-slate-100 sm:text-4xl">Your render job is ready for backend connection.</h1>
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400">
              The form, validation, quote preview, and confirmation state are working. No file was uploaded and no payment was charged because this is currently a frontend-only sandbox.
            </p>

            <dl className="mt-8 grid gap-3 rounded-xl border border-white/[0.07] bg-black/20 p-5 sm:grid-cols-2">
              <div><dt className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Project</dt><dd className="mt-1.5 truncate text-sm text-slate-200">{file?.name}</dd></div>
              <div><dt className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Preview job ID</dt><dd className="mt-1.5 font-mono text-sm text-cyan-200">render_preview_01</dd></div>
              <div><dt className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Workload</dt><dd className="mt-1.5 text-sm capitalize text-slate-200">Blender {version} · {engine}</dd></div>
              <div><dt className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Frame range</dt><dd className="mt-1.5 text-sm text-slate-200">{frameStart}–{frameEnd} · {quote.frameCount} frames</dd></div>
            </dl>

            <div className="mt-8 flex flex-wrap gap-3">
              <button type="button" onClick={reset} className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]">
                <RotateCcw className="h-3.5 w-3.5" /> Create another preview
              </button>
              <button type="button" onClick={() => onNavigate('/app')} className="inline-flex items-center gap-2 rounded-lg border border-white/[0.09] bg-white/[0.025] px-5 py-3 text-xs font-semibold text-slate-300 hover:text-white">
                Return to marketplace
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1380px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
      <button type="button" onClick={() => onNavigate('/app')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 transition-colors hover:text-white">
        <ArrowLeft className="h-3.5 w-3.5" /> Marketplace overview
      </button>

      <div className="mt-6 flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.22em] text-cyan-300">
            <Clapperboard className="h-3.5 w-3.5" /> Render workspace
          </div>
          <h1 className="mt-3 text-3xl font-medium tracking-[-0.035em] text-slate-100 sm:text-4xl">Create a Blender render job</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">Configure the first planned marketplace vertical slice. All rates and capacity shown here are illustrative preview data.</p>
        </div>
        <span className="rounded-full border border-amber-300/15 bg-amber-300/[0.04] px-3 py-1.5 font-mono text-[8px] uppercase tracking-[0.2em] text-amber-300">Sandbox · no upload</span>
      </div>

      <form onSubmit={submit} className="mt-8 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-cyan-300/15 bg-cyan-300/[0.04] text-cyan-300"><HardDriveUpload className="h-4 w-4" /></span>
              <div><h2 className="text-sm font-medium text-slate-100">Project file</h2><p className="mt-1 text-[11px] text-slate-600">Use a packed Blender project with all external assets included.</p></div>
            </div>
            <label className="mt-5 flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.12] bg-black/15 px-5 text-center transition-colors hover:border-cyan-300/30 hover:bg-cyan-300/[0.025]">
              <input type="file" accept=".blend,.zip" required className="sr-only" onChange={(event) => setFile(event.target.files?.[0] || null)} />
              <FileArchive className="h-7 w-7 text-slate-600" />
              <p className="mt-3 text-sm font-medium text-slate-300">{file ? file.name : 'Choose a .blend or .zip project'}</p>
              <p className="mt-1 text-[11px] text-slate-600">Frontend preview only · the selected file stays on your device</p>
            </label>
          </section>

          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-violet-300/15 bg-violet-300/[0.04] text-violet-300"><Film className="h-4 w-4" /></span>
              <div><h2 className="text-sm font-medium text-slate-100">Render configuration</h2><p className="mt-1 text-[11px] text-slate-600">The backend contract will eventually validate every field again.</p></div>
            </div>

            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              <label className="app-field"><span>Blender version</span><select value={version} onChange={(event) => setVersion(event.target.value)}><option value="4.3">Blender 4.3 LTS</option><option value="4.2">Blender 4.2 LTS</option><option value="3.6">Blender 3.6 LTS</option></select></label>
              <label className="app-field"><span>Render engine</span><select value={engine} onChange={(event) => setEngine(event.target.value)}><option value="cycles">Cycles</option><option value="eevee">Eevee</option></select></label>
              <label className="app-field"><span>Start frame</span><input type="number" min="1" value={frameStart} onChange={(event) => setFrameStart(event.target.value)} required /></label>
              <label className="app-field"><span>End frame</span><input type="number" min={frameStart || 1} value={frameEnd} onChange={(event) => setFrameEnd(event.target.value)} required /></label>
              <label className="app-field"><span>Output format</span><select value={output} onChange={(event) => setOutput(event.target.value)}><option value="png">PNG sequence</option><option value="exr">OpenEXR sequence</option><option value="mp4">MP4 preview</option></select></label>
              <label className="app-field"><span>Region preference</span><select value={region} onChange={(event) => setRegion(event.target.value)}><option value="auto">Auto · best value</option><option value="india">India</option><option value="asia">Asia Pacific</option><option value="global">Global</option></select></label>
            </div>
          </section>

          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-amber-300/15 bg-amber-300/[0.04] text-amber-300"><Cpu className="h-4 w-4" /></span>
              <div><h2 className="text-sm font-medium text-slate-100">GPU profile</h2><p className="mt-1 text-[11px] text-slate-600">Choose intent; the scheduler will eventually select the exact verified provider.</p></div>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {GPU_PROFILES.map((profile) => (
                <button key={profile.id} type="button" onClick={() => setGpuProfile(profile.id)} className={`rounded-xl border p-4 text-left transition-all ${gpuProfile === profile.id ? 'border-cyan-300/30 bg-cyan-300/[0.045]' : 'border-white/[0.07] bg-black/10 hover:border-white/[0.13]'}`}>
                  <div className="flex items-center justify-between gap-3"><p className="text-xs font-medium text-slate-200">{profile.label}</p>{gpuProfile === profile.id && <CheckCircle2 className="h-3.5 w-3.5 text-cyan-300" />}</div>
                  <p className="mt-2 font-mono text-[9px] text-slate-600">{profile.gpu}</p>
                  <p className="mt-4 font-mono text-xs text-cyan-200">${profile.previewRate.toFixed(2)}/hr <span className="text-[8px] text-slate-700">preview</span></p>
                </button>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-5 xl:sticky xl:top-[92px] xl:self-start">
          <section className="rounded-xl border border-white/[0.08] bg-[#0d0f17] p-5">
            <div className="flex items-center justify-between"><h2 className="text-sm font-medium text-slate-100">Preview quote</h2><Sparkles className="h-4 w-4 text-indigo-300" /></div>
            <div className="mt-5 space-y-3 border-y border-white/[0.06] py-4 text-xs">
              <div className="flex justify-between gap-4"><span className="text-slate-600">Frames</span><span className="font-mono text-slate-300">{quote.frameCount}</span></div>
              <div className="flex justify-between gap-4"><span className="text-slate-600">GPU profile</span><span className="text-right text-slate-300">{quote.profile.label}</span></div>
              <div className="flex justify-between gap-4"><span className="text-slate-600">Estimated time</span><span className="font-mono text-slate-300">~{quote.estimatedMinutes} min</span></div>
              <div className="flex justify-between gap-4"><span className="text-slate-600">Output</span><span className="uppercase text-slate-300">{output}</span></div>
            </div>
            <div className="mt-5 flex items-end justify-between gap-4">
              <div><p className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Estimated cost</p><p className="mt-1 text-3xl font-medium tracking-[-0.04em] text-slate-100">${quote.estimatedCost}</p></div>
              <span className="pb-1 text-[9px] text-slate-700">Illustrative only</span>
            </div>
            <label className="app-field mt-5"><span>Hard spending limit</span><div className="relative"><span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-600">$</span><input type="number" min="0.10" step="0.10" value={spendingLimit} onChange={(event) => setSpendingLimit(event.target.value)} className="!pl-7" required /></div></label>
            <button type="submit" disabled={!file} className="group mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-100 px-4 py-3 text-xs font-semibold text-[#08090a] transition-all hover:bg-white disabled:cursor-not-allowed disabled:opacity-35">
              Review preview job <ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
            </button>
            {!file && <p className="mt-2 text-center text-[10px] text-slate-700">Choose a project file to continue.</p>}
          </section>

          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5">
            <div className="flex gap-3"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /><div><p className="text-xs font-medium text-slate-300">Planned safety controls</p><p className="mt-2 text-[11px] leading-5 text-slate-600">Disposable sandbox, scoped artifact URLs, network restrictions, timeouts, and verified cleanup before provider release.</p></div></div>
            <div className="mt-4 flex gap-3 border-t border-white/[0.05] pt-4"><Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" /><p className="text-[10px] leading-5 text-slate-600">Final quotes must come from live provider capacity and backend-enforced policies.</p></div>
          </section>
        </aside>
      </form>
    </div>
  );
};

export default RenderJobPage;
