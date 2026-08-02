import React from 'react';
import Logo from './Logo';

const COLS: Array<[string, string[]]> = [
  ['Product', ['Cloud gaming', 'Compute', 'Fabric', 'Status']],
  ['Hosts', ['Start earning', 'Node guides', 'Payouts', 'Safety']],
  ['Company', ['About', 'Careers', 'Press', 'Contact']],
  ['Legal', ['Terms', 'Privacy', 'Rights', 'DMCA']],
];

const Footer: React.FC = () => (
  <footer className="relative border-t border-white/[0.05] bg-[#03040c]">
    <div className="mx-auto max-w-7xl px-6 py-20 sm:px-10">
      {/* Massive wordmark — the closer */}
      <div className="select-none overflow-hidden" aria-hidden="true">
        <p className="serif-display whitespace-nowrap text-[clamp(3.5rem,11vw,10rem)] leading-none text-white/[0.045]">
          NodeForge — liquid hardware
        </p>
      </div>

      <div className="mt-14 grid gap-12 md:grid-cols-[1.2fr_repeat(4,1fr)]">
        <div>
          <a href="#top" className="flex items-center gap-3">
            <Logo className="h-8 w-8" />
            <span className="font-semibold tracking-tight text-slate-100">NodeForge</span>
          </a>
          <p className="mt-5 max-w-xs text-[13.5px] leading-[1.75] text-slate-500">
            The peer-to-peer fabric for GPU compute and cloud gaming.
          </p>
        </div>
        {COLS.map(([head, links]) => (
          <div key={head}>
            <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-slate-600">{head}</p>
            <ul className="mt-4 space-y-2.5">
              {links.map((l) => (
                <li key={l}>
                  <a href="#top" className="text-[13.5px] text-slate-400 transition-colors hover:text-slate-100">
                    {l}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      <div className="mt-16 flex flex-col gap-3 border-t border-white/[0.05] pt-8 font-mono text-[10.5px] uppercase tracking-[0.24em] text-slate-600 sm:flex-row sm:items-center sm:justify-between">
        <span>© 2026 NodeForge Inc</span>
        <span className="text-emerald-500/80">All systems operational</span>
        <span>Est. 2026 · Fabric v1</span>
      </div>
    </div>
  </footer>
);

export default Footer;
