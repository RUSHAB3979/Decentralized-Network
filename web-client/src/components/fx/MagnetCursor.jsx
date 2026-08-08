import React, { useRef } from 'react';
/**
 * Magnetic cursor + trailing comet, drawn once per frame on a fixed overlay canvas.
 * - Mouse is attracted toward the nearest interactive element (a, button, [data-mag]).
 * - A soft trail of fading dots follows the cursor.
 * - Honors prefers-reduced-motion and pointer:coarse (hidden on touch).
 */
const MagnetCursor = () => {
    const layerRef = useRef(null);
    const dotRef = useRef(null);
    const ringRef = useRef(null);
    const canvasRef = useRef(null);
    React.useEffect(() => {
        if (window.matchMedia('(pointer: coarse)').matches)
            return;
        if (window.matchMedia('(prefers-reduced-motion: reduce)').matches)
            return;
        const layer = layerRef.current;
        const dot = dotRef.current;
        const ring = ringRef.current;
        const canvas = canvasRef.current;
        if (!layer || !dot || !ring || !canvas)
            return;
        const ctx = canvas.getContext('2d');
        if (!ctx)
            return;
        let raf = 0;
        let w = 0;
        let h = 0;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const state = {
            x: innerWidth / 2,
            y: innerHeight / 2,
            tx: innerWidth / 2,
            ty: innerHeight / 2,
            rx: innerWidth / 2,
            ry: innerHeight / 2,
            magX: 0,
            magY: 0,
            speed: 0,
        };
        const trail = [];
        const resize = () => {
            w = innerWidth;
            h = innerHeight;
            canvas.width = Math.max(1, Math.floor(w * dpr));
            canvas.height = Math.max(1, Math.floor(h * dpr));
            canvas.style.width = `${w}px`;
            canvas.style.height = `${h}px`;
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };
        resize();
        addEventListener('resize', resize);
        const onMove = (e) => {
            state.tx = e.clientX;
            state.ty = e.clientY;
            state.speed = Math.min(1, state.speed + Math.hypot(e.movementX, e.movementY) * 0.012);
            // Magnetic pull to nearest interactive element
            const el = e.target.closest('a, button, [data-mag]');
            if (el) {
                const r = el.getBoundingClientRect();
                const ex = r.left + r.width / 2 - e.clientX;
                const ey = r.top + r.height / 2 - e.clientY;
                const d = Math.hypot(ex, ey);
                const str = Math.max(0, 1 - d / 120);
                state.magX = ex * 0.18 * str;
                state.magY = ey * 0.18 * str;
            }
            else {
                state.magX *= 0.9;
                state.magY *= 0.9;
            }
        };
        addEventListener('pointermove', onMove, { passive: true });
        const frame = () => {
            // eased follow for dot, softer for ring
            state.x += (state.tx - state.x) * 0.3;
            state.y += (state.ty - state.y) * 0.3;
            state.rx += (state.tx + state.magX * 90 - state.rx) * 0.18;
            state.ry += (state.ty + state.magY * 90 - state.ry) * 0.18;
            state.speed *= 0.92;
            dot.style.transform = `translate(${state.x + state.magX * 60}px, ${state.y + state.magY * 60}px)`;
            ring.style.transform = `translate(${state.rx}px, ${state.ry}px)`;
            ring.style.width = ring.style.height = `${14 + state.speed * 26}px`;
            ring.style.opacity = String(0.35 + state.speed * 0.5);
            trail.push({ x: state.rx, y: state.ry, life: 1 });
            if (trail.length > 26)
                trail.shift();
            ctx.clearRect(0, 0, w, h);
            for (const p of trail) {
                p.life -= 0.02;
                if (p.life <= 0)
                    continue;
                const a = p.life * (0.5 + state.speed * 0.4);
                ctx.fillStyle = `rgba(165,180,252,${(a * 0.22).toFixed(3)})`;
                ctx.beginPath();
                ctx.arc(p.x, p.y, 2.2 + p.life * 2.2, 0, Math.PI * 2);
                ctx.fill();
            }
            raf = requestAnimationFrame(frame);
        };
        raf = requestAnimationFrame(frame);
        document.documentElement.classList.add('has-magnet-cursor');
        return () => {
            cancelAnimationFrame(raf);
            removeEventListener('pointermove', onMove);
            removeEventListener('resize', resize);
            document.documentElement.classList.remove('has-magnet-cursor');
        };
    }, []);
    return (<div ref={layerRef} className="pointer-events-none fixed inset-0 z-[80] hidden md:block" aria-hidden="true">
      <canvas ref={canvasRef} className="absolute inset-0"/>
      <div ref={ringRef} className="absolute -translate-x-1/2 -translate-y-1/2 rounded-full border border-indigo-300" style={{ mixBlendMode: 'screen' }}/>
      <div ref={dotRef} className="absolute -translate-x-1/2 -translate-y-1/2 h-1.5 w-1.5 rounded-full bg-cyan-300" style={{ boxShadow: '0 0 14px rgba(103,232,249,0.9)' }}/>
    </div>);
};
export default MagnetCursor;
