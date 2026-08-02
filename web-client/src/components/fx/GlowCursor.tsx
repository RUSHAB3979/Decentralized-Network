import React, { useEffect, useRef } from 'react';

/**
 * GlowCursor — a soft light that trails the pointer with true spring physics.
 * One rAF loop, transform-only writes (translate3d + scale), GPU-composited.
 * No canvas, no trail spam: smooth at any refresh rate.
 * Hovering interactive elements expands the halo and shifts tint.
 */
const GlowCursor: React.FC = () => {
  const glowRef = useRef<HTMLDivElement>(null);
  const coreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (window.matchMedia('(pointer: coarse)').matches) return;
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const glow = glowRef.current;
    const core = coreRef.current;
    if (!glow || !core) return;

    let raf = 0;
    let targetX = innerWidth / 2;
    let targetY = innerHeight / 2;
    // spring state
    let gx = targetX, gy = targetY, gvx = 0, gvy = 0;
    let cx = targetX, cy = targetY, cvx = 0, cvy = 0;
    let hot = 0; // 0..1 interactive-proximity blend

    const onMove = (e: PointerEvent) => {
      targetX = e.clientX;
      targetY = e.clientY;
      const hit = (e.target as HTMLElement | null)?.closest?.(
        'a, button, [data-mag], [role="button"]',
      );
      if (hit) hot = Math.min(1, hot + 0.25);
    };
    addEventListener('pointermove', onMove, { passive: true });

    let last = performance.now();
    const frame = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;

      // critically-damped spring (stiff enough to feel instant, no wobble)
      const k = 220;
      const damp = 26;
      const step = (x: number, v: number) => {
        const a = (targetX === x && targetY === x ? 0 : 0) + 0;
        return a;
      };
      void step;

      gvx += ((targetX - gx) * k - gvx * damp) * dt;
      gvy += ((targetY - gy) * k - gvy * damp) * dt;
      gx += gvx * dt;
      gy += gvy * dt;

      // core follows faster
      const ck = 420;
      const cd = 40;
      cvx += ((targetX - cx) * ck - cvx * cd) * dt;
      cvy += ((targetY - cy) * ck - cvy * cd) * dt;
      cx += cvx * dt;
      cy += cvy * dt;

      hot = Math.max(0, hot - dt * 2.2);
      const scale = 1 + hot * 1.6;
      const opacity = 0.5 + hot * 0.35;

      glow.style.transform = `translate3d(${gx}px, ${gy}px, 0) translate(-50%,-50%) scale(${scale})`;
      glow.style.opacity = String(opacity);
      core.style.transform = `translate3d(${cx}px, ${cy}px, 0) translate(-50%,-50%) scale(${1 + hot * 0.35})`;
      core.style.background = hot > 0.4
        ? 'rgba(103,232,249,0.95)'
        : 'rgba(165,180,252,0.9)';
      core.style.boxShadow = hot > 0.4
        ? '0 0 22px rgba(103,232,249,0.85)'
        : '0 0 16px rgba(165,180,252,0.7)';

      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    document.documentElement.classList.add('has-glow-cursor');
    return () => {
      cancelAnimationFrame(raf);
      removeEventListener('pointermove', onMove);
      document.documentElement.classList.remove('has-glow-cursor');
    };
  }, []);

  return (
    <div className="pointer-events-none fixed inset-0 z-[80] hidden md:block" aria-hidden="true">
      <div
        ref={glowRef}
        className="absolute h-32 w-32 rounded-full"
        style={{
          background:
            'radial-gradient(circle, rgba(129,140,248,0.16) 0%, rgba(103,232,249,0.07) 40%, transparent 70%)',
          filter: 'blur(6px)',
          willChange: 'transform',
        }}
      />
      <div
        ref={coreRef}
        className="absolute h-2 w-2 rounded-full bg-indigo-300/90"
        style={{ willChange: 'transform' }}
      />
    </div>
  );
};

export default GlowCursor;
