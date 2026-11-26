import React from 'react';
import { ArrowRight } from 'lucide-react';
import LiquidRibbon from './fx/LiquidRibbon';
import Reveal from './fx/Reveal';
const CTA = () => (<section id="cta" className="relative overflow-hidden">
    <div className="hr-fade absolute inset-x-0 top-0 z-10"/>
    <div className="absolute inset-0">
      <LiquidRibbon className="h-full w-full opacity-70"/>
      <div className="absolute inset-0 bg-linear-to-b from-[#03040c] via-transparent to-[#03040c]"/>
    </div>

    <Reveal className="relative mx-auto max-w-4xl px-6 py-44 text-center sm:px-10">
      <p className="eyebrow"><span className="eyebrow-accent"/>GPUOrbit · MVP preview</p>
      <h2 className="serif-display mt-8 text-[clamp(2.8rem,8vw,6rem)] leading-[0.98] text-slate-50">
        See the product,
        <br />
        <em className="serif-italic text-iridescent">before the grid is live.</em>
      </h2>
      <p className="mx-auto mt-7 max-w-lg text-[16.5px] leading-[1.75] text-slate-300/85">
        Customers join by invitation. Providers use the console to manage machines, and an operator approves each machine before it can accept pilot work.
      </p>
      <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
        <a href={import.meta.env.BASE_URL + '#/app'} className="btn-liquid group" data-mag>
          Open the console
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1"/>
        </a>
        <a href="#/provider" className="btn-quiet" data-mag>
          Provider console
        </a>
        <a href="#marketplace" className="btn-quiet" data-mag>
          See capacity preview
        </a>
      </div>
      <p className="mt-8 font-mono text-[10px] uppercase tracking-[0.3em] text-slate-600">
        Preview only · No upload · No payment
      </p>
    </Reveal>
  </section>);
export default CTA;
