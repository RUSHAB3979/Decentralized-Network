import React from 'react';
import {
  ArrowRight,
  ArrowUpRight,
  BrainCircuit,
  CheckCircle2,
  Clapperboard,
  Clock3,
  Cpu,
  Gamepad2,
  MonitorUp,
  Server,
  Sparkles,
} from 'lucide-react';
import { PREVIEW_GPU_OFFERS, PREVIEW_JOBS, WORKLOAD_PRODUCTS } from '../../services/marketplaceData';

const PRODUCT_ICONS = {
  render: Clapperboard,
  models: BrainCircuit,
  workstations: MonitorUp,
  gaming: Gamepad2,
};

const ACCENTS = {
  cyan: 'border-cyan-300/15 bg-cyan-300/[0.045] text-cyan-200',
  violet: 'border-violet-300/15 bg-violet-300/[0.045] text-violet-200',
  amber: 'border-amber-300/15 bg-amber-300/[0.045] text-amber-200',
  emerald: 'border-emerald-300/15 bg-emerald-300/[0.045] text-emerald-200',
};

const MarketplaceDashboard = ({ onNavigate }) => (
  <div className="mx-auto max-w-[1480px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
    <section className="relative overflow-hidden rounded-2xl border border-white/[0.07] bg-[#0c0e16] px-6 py-8 sm:px-9 sm:py-10">
      <div className="pointer-events-none absolute -right-24 -top-36 h-80 w-80 rounded-full bg-indigo-500/[0.14] blur-[100px]" />
      <div className="pointer-events-none absolute bottom-[-70%] left-[35%] h-80 w-80 rounded-full bg-cyan-400/[0.08] blur-[110px]" />
      <div className="relative grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <div className="inline-flex items-center gap-2 rounded-full border border-indigo-300/15 bg-indigo-300/[0.05] px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.2em] text-indigo-200">
            <Sparkles className="h-3 w-3" /> Unified GPU marketplace
          </div>
          <h1 className="mt-5 max-w-3xl text-[clamp(2rem,5vw,4.2rem)] font-medium leading-[1.02] tracking-[-0.045em] text-[#f7f8f8]">
            Turn an idea into GPU work,
            <span className="block text-slate-500">without owning the machine.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-[15px] leading-7 text-slate-400">
            Render creative projects, call open models, or reserve an interactive workstation through one verified compute fabric.
          </p>
        </div>
        <div className="flex flex-wrap gap-3 lg:justify-end">
          <button type="button" onClick={() => onNavigate('/app/render')} className="group inline-flex items-center gap-2 rounded-lg bg-[#f7f8f8] px-5 py-3 text-xs font-semibold text-[#08090a] transition-transform hover:-translate-y-0.5">
            Create render job
            <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" />
          </button>
          <button type="button" onClick={() => onNavigate('/provider')} className="inline-flex items-center gap-2 rounded-lg border border-white/[0.09] bg-white/[0.025] px-5 py-3 text-xs font-semibold text-slate-200 hover:bg-white/[0.05]">
            <Server className="h-3.5 w-3.5" /> Provide a GPU
          </button>
        </div>
      </div>
    </section>

    <section className="mt-10">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="font-mono text-[9px] uppercase tracking-[0.24em] text-slate-600">Choose a workflow</p>
          <h2 className="mt-2 text-xl font-medium tracking-[-0.025em] text-slate-100">One fabric, four product experiences</h2>
        </div>
        <p className="text-xs text-slate-600">Capabilities are released behind reliability and security gates.</p>
      </div>
      <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {WORKLOAD_PRODUCTS.map((product) => {
          const Icon = PRODUCT_ICONS[product.id];
          return (
            <button key={product.id} type="button" onClick={() => onNavigate(product.route)} className="group flex min-h-[240px] flex-col rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 text-left transition-all hover:-translate-y-1 hover:border-white/[0.13] hover:bg-white/[0.032]">
              <div className={`flex h-10 w-10 items-center justify-center rounded-lg border ${ACCENTS[product.accent]}`}>
                <Icon className="h-[18px] w-[18px]" />
              </div>
              <p className="mt-5 font-mono text-[8px] uppercase tracking-[0.22em] text-slate-600">{product.eyebrow}</p>
              <h3 className="mt-2 text-lg font-medium tracking-[-0.02em] text-slate-100">{product.title}</h3>
              <p className="mt-2 text-[13px] leading-6 text-slate-500">{product.description}</p>
              <span className="mt-auto flex items-center gap-1.5 pt-5 text-[11px] font-medium text-slate-300">
                {product.action}<ArrowUpRight className="h-3 w-3 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </span>
            </button>
          );
        })}
      </div>
    </section>

    <div className="mt-10 grid gap-5 xl:grid-cols-[1.35fr_.65fr]">
      <section className="overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.018]">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <div>
            <h2 className="text-sm font-medium text-slate-100">GPU capacity preview</h2>
            <p className="mt-1 text-[11px] text-slate-600">Illustrative offers until the live provider API is connected.</p>
          </div>
          <span className="rounded-full border border-amber-300/15 bg-amber-300/[0.04] px-2.5 py-1 font-mono text-[8px] uppercase tracking-[0.18em] text-amber-300">Mock data</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[680px] text-left">
            <thead className="border-b border-white/[0.05] font-mono text-[8px] uppercase tracking-[0.2em] text-slate-700">
              <tr>
                <th className="px-5 py-3 font-medium">GPU</th>
                <th className="px-5 py-3 font-medium">Region</th>
                <th className="px-5 py-3 font-medium">Good for</th>
                <th className="px-5 py-3 font-medium">Preview rate</th>
                <th className="px-5 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.05]">
              {PREVIEW_GPU_OFFERS.map((offer) => (
                <tr key={offer.id} className="transition-colors hover:bg-white/[0.02]">
                  <td className="px-5 py-4"><p className="text-[13px] font-medium text-slate-200">{offer.gpu}</p><p className="mt-1 font-mono text-[9px] text-slate-600">{offer.vram} VRAM</p></td>
                  <td className="px-5 py-4 text-xs text-slate-400">{offer.region}</td>
                  <td className="px-5 py-4 text-xs text-slate-500">{offer.fit}</td>
                  <td className="px-5 py-4 font-mono text-xs text-cyan-200">{offer.rate}</td>
                  <td className="px-5 py-4"><span className="inline-flex items-center gap-1.5 text-[10px] text-slate-500"><span className="h-1.5 w-1.5 rounded-full bg-amber-300" />{offer.availability}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="rounded-xl border border-white/[0.07] bg-white/[0.018]">
        <div className="border-b border-white/[0.06] px-5 py-4">
          <h2 className="text-sm font-medium text-slate-100">Workflow preview</h2>
          <p className="mt-1 text-[11px] text-slate-600">Representative records, not live jobs.</p>
        </div>
        <div className="divide-y divide-white/[0.05]">
          {PREVIEW_JOBS.map((job) => (
            <div key={job.id} className="p-5">
              <div className="flex items-start gap-3">
                <span className={`mt-0.5 flex h-8 w-8 items-center justify-center rounded-lg border ${job.status === 'completed' ? 'border-emerald-300/15 bg-emerald-300/[0.04] text-emerald-300' : 'border-indigo-300/15 bg-indigo-300/[0.04] text-indigo-300'}`}>
                  {job.status === 'completed' ? <CheckCircle2 className="h-4 w-4" /> : <Clock3 className="h-4 w-4" />}
                </span>
                <div className="min-w-0">
                  <p className="truncate text-xs font-medium text-slate-200">{job.name}</p>
                  <p className="mt-1 text-[10px] text-slate-600">{job.type} · {job.detail}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        <button type="button" onClick={() => onNavigate('/app/render')} className="mx-4 mb-4 mt-3 flex w-[calc(100%_-_2rem)] items-center justify-center gap-2 rounded-lg border border-white/[0.07] bg-white/[0.025] py-2.5 text-[11px] font-medium text-slate-400 hover:text-white">
          <Cpu className="h-3.5 w-3.5" /> Open render workspace
        </button>
      </section>
    </div>
  </div>
);

export default MarketplaceDashboard;
