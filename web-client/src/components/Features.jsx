import React from 'react';
import { Gauge, ShieldCheck, Boxes, Wallet, Network, Scale } from 'lucide-react';
import Reveal from './fx/Reveal';
const FEATURES = [
    { icon: Gauge, title: 'Workload-aware matching.', body: 'VRAM, region, runtime, cache, price, and reliability shape every placement.' },
    { icon: ShieldCheck, title: 'Curated before arbitrary.', body: 'Signed runtimes and disposable sandboxes protect customers and providers.' },
    { icon: Boxes, title: 'Three execution primitives.', body: 'Batch jobs, long-running deployments, and interactive sessions share one control plane.' },
    { icon: Wallet, title: 'Auditable metering.', body: 'Quotes, spending caps, usage, refunds, and provider earnings use one ledger.' },
    { icon: Network, title: 'Purpose-built data paths.', body: 'Artifacts, inference requests, and streams move through different secure paths.' },
    { icon: Scale, title: 'Permission by design.', body: 'Open-source license review and BYOL controls are product requirements, not footnotes.' },
];
const Features = () => (<section id="features" className="relative">
    <div className="hr-fade absolute inset-x-0 top-0"/>
    <div className="mx-auto max-w-7xl px-6 py-32 sm:px-10">
      <Reveal>
        <p className="eyebrow"><span className="eyebrow-accent"/>The fabric</p>
        <h2 className="serif-display mt-6 max-w-2xl text-[clamp(2.2rem,5vw,4rem)] leading-[1.02] text-slate-50">
          Built as infrastructure,
          <br />
          experienced as a <em className="serif-italic text-iridescent">product.</em>
        </h2>
      </Reveal>

      <div className="mt-20 grid gap-x-12 gap-y-12 sm:grid-cols-2 lg:grid-cols-3">
        {FEATURES.map((f, i) => (<Reveal key={f.title} delay={(i % 3) * 110}>
            <div className="group border-t border-white/[0.07] pt-7 transition-colors hover:border-cyan-400/30">
              <f.icon className="h-5 w-5 text-slate-500 transition-colors group-hover:text-cyan-300"/>
              <h3 className="mt-5 text-[17px] font-semibold tracking-tight text-slate-100">{f.title}</h3>
              <p className="mt-2.5 max-w-[36ch] text-[14.5px] leading-[1.75] text-slate-400">{f.body}</p>
            </div>
          </Reveal>))}
      </div>
    </div>
  </section>);
export default Features;
