import React, { useState } from 'react';
import Reveal from './fx/Reveal';
const ROWS = [
    { id: 'RTX 3060 · 12GB', meta: 'Blender · SDXL', play: '$0.12/hr', host: '$9.20/day' },
    { id: 'RTX 4070 Ti · 16GB', meta: 'Cycles · Video AI', play: '$0.24/hr', host: '$18.40/day', hot: true },
    { id: 'RTX 4090 · 24GB', meta: 'LLMs · 4K render', play: '$0.46/hr', host: '$36.90/day' },
];
const Marketplace = () => {
    const [mode, setMode] = useState('play');
    return (<section id="marketplace" className="relative">
      <div className="hr-fade absolute inset-x-0 top-0"/>
      <div className="mx-auto max-w-7xl px-6 py-32 sm:px-10">
        <div className="grid gap-16 lg:grid-cols-[1fr_1.05fr] lg:items-center">
          <Reveal>
            <p className="eyebrow"><span className="eyebrow-accent"/>Marketplace</p>
            <h2 className="serif-display mt-6 text-[clamp(2.2rem,5vw,4rem)] leading-[1.02] text-slate-50">
              A spot market
              <br />
              for <em className="serif-italic text-iridescent">silicon.</em>
            </h2>
            <p className="mt-6 max-w-md text-[17px] leading-[1.75] text-slate-400">
              Illustrative compute capacity by workload and region. Listings below are examples, not real GPU offers.
            </p>

            <div className="mt-10 inline-flex rounded-full border border-white/10 bg-white/[0.02] p-1">
              {['play', 'host'].map((m) => (<button key={m} onClick={() => setMode(m)} data-mag className={`rounded-full px-6 py-2.5 text-[12.5px] font-semibold uppercase tracking-[0.14em] transition-all ${mode === m ? 'bg-slate-100 text-[#03040c]' : 'text-slate-500 hover:text-slate-200'}`}>
                  {m === 'play' ? 'Rent compute' : 'Provide a GPU'}
                </button>))}
            </div>

            <div className="mt-10 border-l border-cyan-400/40 pl-6">
              <p className="eyebrow !text-[10px]">{mode === 'play' ? 'Preview price' : 'Preview earning model'}</p>
              <p className="num-mono-huge mt-2 text-4xl text-slate-50">
                {mode === 'play' ? '$0.12/hr' : 'Usage based'}
              </p>
            </div>
          </Reveal>

          <Reveal delay={140}>
            <div className="glass-hairline overflow-hidden">
              <div className="flex items-center justify-between border-b border-white/[0.06] px-7 py-4">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.3em] text-slate-500">
                  Capacity board — preview
                </span>
                <span className="flex items-center gap-2 font-mono text-[10.5px] text-emerald-400">
                  <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-emerald-400"/>
                  MOCK DATA
                </span>
              </div>
              {ROWS.map((r, i) => (<div key={r.id} className={`flex items-center justify-between px-7 py-6 transition-colors hover:bg-white/[0.03] ${i < ROWS.length - 1 ? 'border-b border-white/[0.05]' : ''}`}>
                  <div>
                    <div className="flex items-center gap-3">
                      <p className="font-medium tracking-tight text-slate-100">{r.id}</p>
                      {r.hot && (<span className="rounded-full border border-fuchsia-400/30 bg-fuchsia-400/10 px-2 py-0.5 font-mono text-[9px] uppercase tracking-[0.2em] text-fuchsia-300">
                          Example
                        </span>)}
                    </div>
                    <p className="mt-1.5 font-mono text-[10.5px] uppercase tracking-[0.22em] text-slate-500">
                      {r.meta}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-[9.5px] uppercase tracking-[0.28em] text-slate-600">
                      {mode === 'play' ? 'you pay' : 'you earn'}
                    </p>
                    <p className="num-mono-huge mt-1.5 text-xl text-cyan-200">
                      {mode === 'play' ? r.play : r.host}
                    </p>
                  </div>
                </div>))}
            </div>
          </Reveal>
        </div>
      </div>
    </section>);
};
export default Marketplace;
