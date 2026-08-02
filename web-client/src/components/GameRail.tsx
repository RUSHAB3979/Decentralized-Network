import React from 'react';
import { ArrowUpRight, Gamepad2 } from 'lucide-react';
import Reveal from './fx/Reveal';

const GAMES = [
  { name: 'Elden Ring', note: 'Soulslike', bar: 'from-amber-400/60' },
  { name: 'Baldur\u2019s Gate 3', note: 'CRPG', bar: 'from-rose-400/60' },
  { name: 'Cyberpunk 2077', note: 'Open world', bar: 'from-cyan-400/60' },
  { name: 'Helldivers 2', note: 'Co-op', bar: 'from-emerald-400/60' },
];

const GameRail: React.FC = () => (
  <section id="games" className="relative">
    <div className="hr-fade absolute inset-x-0 top-0" />
    <div className="mx-auto max-w-7xl px-6 py-32 sm:px-10">
      <Reveal className="flex flex-wrap items-end justify-between gap-6">
        <div>
          <p className="eyebrow"><span className="eyebrow-accent" />Catalog</p>
          <h2 className="serif-display mt-6 text-[clamp(2rem,4.5vw,3.5rem)] leading-[1.02] text-slate-50">
            480+ titles.
            <br />
            <em className="serif-italic text-iridescent">Zero installs.</em>
          </h2>
        </div>
        <a
          href="#cta"
          className="group inline-flex items-center gap-2 text-[13px] font-semibold uppercase tracking-[0.14em] text-slate-300 transition-colors hover:text-white"
          data-mag
        >
          Full catalog
          <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
        </a>
      </Reveal>

      {/* Hairline table of games — no cards, pure type */}
      <div className="mt-16">
        {GAMES.map((g, i) => (
          <Reveal key={g.name} delay={i * 90}>
            <a
              href="#cta"
              className="group flex items-center justify-between border-t border-white/[0.06] py-6 transition-colors hover:bg-white/[0.015]"
            >
              <div className="flex items-center gap-6">
                <Gamepad2 className="h-4.5 w-4.5 h-[18px] w-[18px] text-slate-600 transition-colors group-hover:text-cyan-300" />
                <div>
                  <p className="serif-display text-2xl text-slate-100 transition-transform duration-300 group-hover:translate-x-1.5">
                    {g.name}
                  </p>
                  <p className="mt-0.5 font-mono text-[10px] uppercase tracking-[0.26em] text-slate-500">
                    {g.note}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-5">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-slate-500 transition-colors group-hover:text-slate-300">
                  Play now
                </span>
                <span className={`h-10 w-0.5 rounded bg-gradient-to-b ${g.bar} to-transparent opacity-40 transition-opacity group-hover:opacity-100`} />
              </div>
            </a>
          </Reveal>
        ))}
      </div>
    </div>
  </section>
);

export default GameRail;
