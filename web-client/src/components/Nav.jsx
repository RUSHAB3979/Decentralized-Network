import React, { useEffect, useState } from 'react';
import { ArrowUpRight } from 'lucide-react';
import Logo from './Logo';
const LINKS = [
    ['Products', '#features'],
    ['How it works', '#how'],
    ['Market', '#marketplace'],
    ['Providers', '#marketplace'],
];
const consoleUrl = import.meta.env.BASE_URL + '#/app';
const Nav = () => {
    const [scrolled, setScrolled] = useState(false);
    useEffect(() => {
        const on = () => setScrolled(window.scrollY > 40);
        addEventListener('scroll', on, { passive: true });
        on();
        return () => removeEventListener('scroll', on);
    }, []);
    return (<header className={`fixed inset-x-0 top-0 z-[60] transition-all duration-500 ${scrolled ? 'bg-[#03040c]/70 backdrop-blur-xl border-b border-white/[0.06]' : 'bg-transparent'}`}>
      <nav className="mx-auto flex h-[74px] max-w-7xl items-center justify-between px-6 sm:px-10">
        <a href="#top" className="flex items-center gap-3" data-mag>
          <Logo className="h-8 w-8"/>
          <span className="flex flex-col leading-none">
            <span className="font-semibold tracking-tight text-[15px]">GPUOrbit</span>
            <span className="mt-1 font-mono text-[9px] uppercase tracking-[0.32em] text-slate-500">
              P2P Compute
            </span>
          </span>
        </a>

        <div className="hidden md:flex items-center gap-9">
          {LINKS.map(([l, href]) => (<a key={l} href={href} className="group relative text-[13px] font-medium tracking-wide text-slate-400 transition-colors hover:text-slate-100">
              {l}
              <span className="absolute -bottom-1.5 left-0 h-px w-0 bg-linear-to-r from-cyan-400 to-violet-400 transition-all duration-300 group-hover:w-full"/>
            </a>))}
        </div>

        <a href={consoleUrl} className="group inline-flex items-center gap-1.5 rounded-full border border-white/15 px-5 py-2.5 text-[12.5px] font-semibold tracking-wide text-slate-100 transition-all hover:border-white/30 hover:bg-white/[0.04]" data-mag>
          Open console
          <ArrowUpRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"/>
        </a>
      </nav>
    </header>);
};
export default Nav;
