import React from 'react';
import { ArrowUpRight, BrainCircuit, Clapperboard, Gamepad2, MonitorUp } from 'lucide-react';
import Reveal from './fx/Reveal';
const WORKLOADS = [
    { name: 'Render & media', note: 'Batch jobs', route: '/app/render', icon: Clapperboard, bar: 'from-cyan-400/60', action: 'Create job' },
    { name: 'Open model APIs', note: 'Deployments', route: '/app/models', icon: BrainCircuit, bar: 'from-violet-400/60', action: 'Explore APIs' },
    { name: 'GPU workstations', note: 'Interactive sessions', route: '/app/workstations', icon: MonitorUp, bar: 'from-amber-400/60', action: 'View profiles' },
    { name: 'Cloud gaming', note: 'Permission gated', route: '/app/gaming', icon: Gamepad2, bar: 'from-emerald-400/60', action: 'View track' },
];
const GameRail = () => (<section id="workloads" className="relative">
    <div className="hr-fade absolute inset-x-0 top-0"/>
    <div className="mx-auto max-w-7xl px-6 py-32 sm:px-10">
      <Reveal className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="eyebrow"><span className="eyebrow-accent"/>Workloads</p>
          <h2 className="serif-display mt-6 text-[clamp(2rem,4.5vw,3.5rem)] leading-[1.02] text-slate-50">
            One marketplace.
            <br />
            <em className="serif-italic text-iridescent">Four ways to compute.</em>
          </h2>
        </div>
        <a href={import.meta.env.BASE_URL + '#/app'} className="group inline-flex items-center gap-2 text-[13px] font-semibold uppercase tracking-[0.14em] text-slate-300 transition-colors hover:text-white" data-mag>
          Open console
          <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"/>
        </a>
      </Reveal>

      {/* Hairline table of product workflows — no cards, pure type */}
      <div className="mt-16">
        {WORKLOADS.map((workload, i) => {
          const WorkloadIcon = workload.icon;
          return (<Reveal key={workload.name} delay={i * 90}>
            <a href={import.meta.env.BASE_URL + '#' + workload.route} className="group flex items-center justify-between border-t border-white/[0.06] py-6 transition-colors hover:bg-white/[0.015]">
              <div className="flex items-center gap-6">
                <WorkloadIcon className="h-[18px] w-[18px] text-slate-600 transition-colors group-hover:text-cyan-300"/>
                <div>
                  <p className="serif-display text-2xl text-slate-100 transition-transform duration-300 group-hover:translate-x-1.5">
                    {workload.name}
                  </p>
                  <p className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.26em] text-slate-500">
                    {workload.note}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-5">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-slate-500 transition-colors group-hover:text-slate-300">
                  {workload.action}
                </span>
                <span className={`h-10 w-0.5 rounded bg-gradient-to-b ${workload.bar} to-transparent opacity-40 transition-opacity group-hover:opacity-100`}/>
              </div>
            </a>
          </Reveal>);
        })}
      </div>
    </div>
  </section>);
export default GameRail;
