import React, { useEffect, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import LiquidRibbon from './fx/LiquidRibbon';
import Reveal from './fx/Reveal';
const signupUrl = import.meta.env.BASE_URL + 'signup';
const TICKER = [
    'EU-WEST · 9MS', 'US-EAST · 11MS', 'GPU-SEC/MIN 1.24M', 'AV1 · 4K120',
    'HOST SETTLE $3.84/HR', 'AP-SOUTHEAST · 14MS', 'NODES 2,431', 'UPTIME 99.95%',
];
const STATS = [
    { v: '8ms', l: 'Median latency' },
    { v: '2,431', l: 'Live nodes' },
    { v: '$0.12/hr', l: 'From price' },
    { v: '99.95%', l: 'Uptime' },
];
const Hero = () => {
    const [mounted, setMounted] = useState(false);
    useEffect(() => setMounted(true), []);
    return (<section id="top" className="relative min-h-[100svh] flex flex-col overflow-hidden">
      {/* Backdrop layers */}
      <div className="absolute inset-0 bg-grid-blueprint mask-fade-y opacity-70"/>
      <div className="absolute inset-0">
        <LiquidRibbon className="h-full w-full"/>
      </div>
      {/* Bottom fade into page */}
      <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-b from-transparent to-[#03040c]"/>

      {/* Center composition */}
      <div className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 pt-28 pb-40 text-center">
        <Reveal>
          <p className="eyebrow">
            <span className="eyebrow-accent"/>
            Peer-to-peer GPU fabric
            <span className="eyebrow-accent !mr-0 ml-4 !bg-gradient-to-l"/>
          </p>

          <h1 className="serif-display mt-8 text-[clamp(3.2rem,9vw,7.75rem)] leading-[0.96] text-slate-50" style={{ textShadow: '0 0 80px rgba(103,232,249,0.12)' }}>
            The world&rsquo;s
            <br />
            idle silicon,
            <br />
            <em className="serif-italic text-iridescent">liquid</em> for everyone.
          </h1>

          <p className="mx-auto mt-8 max-w-xl text-[17px] leading-[1.75] text-slate-300/90">
            NodeForge melts stranded GPUs into a single peer-to-peer pool —
            stream AAA games from a neighbor&rsquo;s rig, or rent your own hardware
            while you sleep.
          </p>

          <div className="mt-12 flex flex-wrap items-center justify-center gap-4">
            <a href={signupUrl} className="btn-liquid group" data-mag>
              Start playing free
              <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1"/>
            </a>
            <a href="#marketplace" className="btn-quiet" data-mag>
              Become a host
            </a>
          </div>
        </Reveal>
      </div>

      {/* Scrolling telemetry ticker above stats */}
      <div className="relative z-10 overflow-hidden mask-fade-edges-x pb-8">
        <div className="animate-marquee-x inline-flex whitespace-nowrap items-center">
          {[0, 1].map((rep) => (<React.Fragment key={rep}>
              {TICKER.map((t) => (<span key={`${rep}-${t}`} className="mx-8 flex items-center gap-3 text-[11px] font-mono uppercase tracking-[0.3em] text-slate-500">
                  <span className="h-1 w-1 rounded-full bg-cyan-400/70"/>
                  {t}
                </span>))}
            </React.Fragment>))}
        </div>
      </div>

      {/* Stats hairline */}
      <div className="relative z-10 border-t border-white/[0.07]">
        <div className="mx-auto grid max-w-6xl grid-cols-2 md:grid-cols-4">
          {STATS.map((s) => (<div key={s.l} className="group px-8 py-6 text-center">
              <p className="num-mono-huge text-2xl text-slate-50 transition-colors group-hover:text-cyan-200">
                {s.v}
              </p>
              <p className="mt-1 text-[10px] uppercase tracking-[0.28em] text-slate-500">{s.l}</p>
            </div>))}
        </div>
      </div>
    </section>);
};
export default Hero;
