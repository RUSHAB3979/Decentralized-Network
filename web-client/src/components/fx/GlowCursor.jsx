import React, { useEffect, useRef } from 'react';
/**
 * GlowCursor — a soft halo that trails the pointer, plus a core dot that *is* the
 * pointer (the native cursor is hidden while this is mounted, see `.has-glow-cursor`).
 *
 * Two rules follow from that:
 *   1. The core never lags. It is written straight from the pointer event, so it
 *      cannot drift away from where the user thinks their cursor is.
 *   2. The halo trails with an analytically-solved critically damped spring, which
 *      is stable at any frame rate and never overshoots.
 *
 * Position and scale go through the standalone `translate`/`scale` properties rather
 * than one `transform` string, so they compose without fighting each other and stay
 * on the compositor.
 */

/**
 * Exact solution of a critically damped spring over `dt`.
 *
 * The previous implementation integrated `v += ((target - x) * k - v * damp) * dt`
 * with `dt` clamped to 50ms. Explicit Euler needs `damp * dt < 2` to converge, and
 * the core's damping of 40 hits exactly 2.0 at that clamp — so any frame at or below
 * 20fps made the dot diverge and fly off-screen instead of settling. Solving the ODE
 * in closed form removes the stability limit entirely: large `dt` simply means
 * "arrived", which is the correct behaviour after a stall or a background tab.
 */
const springStep = (pos, vel, target, omega, dt) => {
    const decay = Math.exp(-omega * dt);
    const dx = pos - target;
    const dv = vel + omega * dx;
    const next = dx + dv * dt;
    return [target + next * decay, (dv - omega * next) * decay];
};

/** Frame-rate independent ease toward a target. */
const approach = (value, target, rate, dt) => value + (target - value) * (1 - Math.exp(-rate * dt));

const GlowCursor = () => {
    const glowRef = useRef(null);
    const coreRef = useRef(null);
    useEffect(() => {
        if (window.matchMedia('(pointer: coarse)').matches)
            return;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches)
            return;
        const glow = glowRef.current;
        const core = coreRef.current;
        if (!glow || !core)
            return;

        let raf = 0;
        let running = false;
        let last = 0;

        let targetX = innerWidth / 2;
        let targetY = innerHeight / 2;
        // Halo spring state. The core has none — it is pinned to the pointer.
        let gx = targetX, gy = targetY, gvx = 0, gvy = 0;
        let hovering = 0; // 1 while over an interactive element
        let hot = 0; // eased blend toward `hovering`
        let onScreen = 0; // 1 once the pointer has been seen, 0 when it leaves
        let appear = 0; // eased blend toward `onScreen`
        let warm = null; // last written tint, so we only touch paint properties on change

        // The halo settles in ~180ms: present enough to read as a trail, short
        // enough that it never feels like it is dragging behind the pointer.
        const HALO_OMEGA = 26;

        const placeCore = () => {
            core.style.translate = `${targetX}px ${targetY}px`;
        };

        const wake = () => {
            if (running)
                return;
            running = true;
            last = performance.now();
            raf = requestAnimationFrame(frame);
        };

        const onMove = (e) => {
            targetX = e.clientX;
            targetY = e.clientY;
            hovering = e.target?.closest?.('a, button, [data-mag], [role="button"]') ? 1 : 0;
            onScreen = 1;
            // Written here rather than in the rAF loop so the dot lands on the
            // pointer in the very next paint, with no frame of latency added.
            placeCore();
            wake();
        };

        const onLeave = () => {
            onScreen = 0;
            hovering = 0;
            wake();
        };

        const frame = (now) => {
            const dt = Math.max(0, (now - last) / 1000);
            last = now;

            [gx, gvx] = springStep(gx, gvx, targetX, HALO_OMEGA, dt);
            [gy, gvy] = springStep(gy, gvy, targetY, HALO_OMEGA, dt);
            hot = approach(hot, hovering, 12, dt);
            appear = approach(appear, onScreen, 14, dt);

            glow.style.translate = `${gx}px ${gy}px`;
            glow.style.scale = String(1 + hot * 1.6);
            glow.style.opacity = String((0.5 + hot * 0.35) * appear);
            core.style.scale = String(1 + hot * 0.35);
            core.style.opacity = String(appear);

            const nextWarm = hot > 0.4;
            if (nextWarm !== warm) {
                warm = nextWarm;
                core.style.background = nextWarm ? 'rgba(103,232,249,0.95)' : 'rgba(165,180,252,0.9)';
                core.style.boxShadow = nextWarm
                    ? '0 0 22px rgba(103,232,249,0.85)'
                    : '0 0 16px rgba(165,180,252,0.7)';
            }

            const settled = Math.abs(gx - targetX) < 0.05 && Math.abs(gy - targetY) < 0.05
                && Math.abs(gvx) < 0.05 && Math.abs(gvy) < 0.05
                && Math.abs(hot - hovering) < 0.005 && Math.abs(appear - onScreen) < 0.005;
            if (settled) {
                // Snap off the residue and idle until the pointer moves again.
                gx = targetX;
                gy = targetY;
                gvx = 0;
                gvy = 0;
                hot = hovering;
                appear = onScreen;
                running = false;
                return;
            }
            raf = requestAnimationFrame(frame);
        };

        placeCore();
        addEventListener('pointermove', onMove, { passive: true });
        document.addEventListener('pointerleave', onLeave);
        addEventListener('blur', onLeave);
        document.documentElement.classList.add('has-glow-cursor');
        wake();
        return () => {
            cancelAnimationFrame(raf);
            running = false;
            removeEventListener('pointermove', onMove);
            document.removeEventListener('pointerleave', onLeave);
            removeEventListener('blur', onLeave);
            document.documentElement.classList.remove('has-glow-cursor');
        };
    }, []);
    return (<div className="pointer-events-none fixed inset-0 z-[80] hidden md:block" aria-hidden="true">
      <div ref={glowRef} className="absolute left-0 top-0 -ml-16 -mt-16 h-32 w-32 rounded-full opacity-0" style={{
            background: 'radial-gradient(circle, rgba(129,140,248,0.16) 0%, rgba(103,232,249,0.07) 40%, transparent 70%)',
            filter: 'blur(6px)',
            willChange: 'translate, scale, opacity',
        }}/>
      <div ref={coreRef} className="absolute left-0 top-0 -ml-1 -mt-1 h-2 w-2 rounded-full bg-indigo-300/90 opacity-0" style={{ willChange: 'translate, scale' }}/>
    </div>);
};
export default GlowCursor;
