import React from 'react';
import { MonitorPlay, Waypoints, TimerReset } from 'lucide-react';
import Reveal from './fx/Reveal';

const STEPS = [
  {
    n: 'I',
    icon: MonitorPlay,
    title: 'Pick a title, or a job.',
    body: 'Gaming sessions and compute jobs enter the same queue. One fabric, one meter.',
  },
  {
    n: 'II',
    icon: Waypoints,
    title: 'Routed in milliseconds.',
    body: 'Edge matchmaking claims the nearest verified node; WebRTC opens a direct path.',
  },
  {
    n: 'III',
    icon: TimerReset,
    title: 'Settled per second.',
    body: 'Hosts are paid per GPU-second, instantly. Players pay only while pixels flow.',
  },
];

const HowItWorks: React.FC = () => (
  <section id="how" className="relative">
    <div className="hr-fade absolute inset-x-0 top-0" />
    <div className="mx-auto max-w-7xl px-6 py-32 sm:px-10">
      <Reveal>
        <p className="eyebrow"><span className="eyebrow-accent" />The loop</p>
        <h2 className="serif-display mt-6 text-[clamp(2.2rem,5vw,4rem)] leading-[1.02] text-slate-50">
          From intent to pixels,
          <br />
          in <em className="serif-italic text-iridescent">three</em> movements.
        </h2>
      </Reveal>

      <div className="mt-20 grid gap-x-14 gap-y-14 md:grid-cols-3">
        {STEPS.map((s, i) => (
          <Reveal key={s.n} delay={i * 130}>
            <div className="group">
              <div className="flex items-center justify-between">
                <span className="serif-display text-5xl text-slate-700/80 transition-colors duration-500 group-hover:text-iridescent group-hover:text-cyan-200/70">
                  {s.n}
                </span>
                <s.icon className="h-5 w-5 text-slate-600 transition-colors group-hover:text-cyan-300" />
              </div>
              <div className="mt-6 h-px w-full bg-white/[0.06] transition-colors duration-500 group-hover:bg-cyan-400/30" />
              <h3 className="mt-6 text-[19px] font-semibold tracking-tight text-slate-100">{s.title}</h3>
              <p className="mt-3 max-w-[34ch] text-[15px] leading-[1.75] text-slate-400">{s.body}</p>
            </div>
          </Reveal>
        ))}
      </div>
    </div>
  </section>
);

export default HowItWorks;
