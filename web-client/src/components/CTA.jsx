import React from 'react';
import { ArrowRight } from 'lucide-react';
import LiquidRibbon from './fx/LiquidRibbon';
import Reveal from './fx/Reveal';
const CTA = () => (<section id="cta" className="relative overflow-hidden">
    <div className="hr-fade absolute inset-x-0 top-0 z-10"/>
    <div className="absolute inset-0">
      <LiquidRibbon className="h-full w-full opacity-70"/>
      <div className="absolute inset-0 bg-gradient-to-b from-[#03040c] via-transparent to-[#03040c]"/>
    </div>

    <Reveal className="relative mx-auto max-w-4xl px-6 py-44 text-center sm:px-10">
      <p className="eyebrow"><span className="eyebrow-accent"/>Early access — now open</p>
      <h2 className="serif-display mt-8 text-[clamp(2.8rem,8vw,6rem)] leading-[0.98] text-slate-50">
        The grid is live.
        <br />
        <em className="serif-italic text-iridescent">Claim your seat.</em>
      </h2>
      <p className="mx-auto mt-7 max-w-lg text-[16.5px] leading-[1.75] text-slate-300/85">
        Five free streaming hours at launch for players. Double settlement for hosts during
        the first thirty days.
      </p>
      <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
        <a href="#top" className="btn-liquid group" data-mag>
          Claim early access
          <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1"/>
        </a>
        <a href="#marketplace" className="btn-quiet" data-mag>
          See the order book
        </a>
      </div>
      <p className="mt-8 font-mono text-[10px] uppercase tracking-[0.3em] text-slate-600">
        No subscription · No install · No region locks
      </p>
    </Reveal>
  </section>);
export default CTA;
