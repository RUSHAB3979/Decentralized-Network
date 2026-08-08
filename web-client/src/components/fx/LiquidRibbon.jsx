import React, { useEffect, useRef } from 'react';
/**
 * LiquidRibbon — a slow iridescent fluid band rendered on canvas.
 * Layered sine fields + drifting palette, reacts softly to the pointer.
 * The NodeForge signature backdrop.
 */
const LiquidRibbon = ({ className = '' }) => {
    const canvasRef = useRef(null);
    const mouse = useRef({ x: -1000, y: -1000, energy: 0 });
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas)
            return;
        const ctx = canvas.getContext('2d');
        if (!ctx)
            return;
        let w = 0;
        let h = 0;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const resize = () => {
            const r = canvas.parentElement?.getBoundingClientRect();
            w = r ? r.width : innerWidth;
            h = r ? r.height : innerHeight;
            canvas.width = Math.max(1, Math.floor(w * dpr));
            canvas.height = Math.max(1, Math.floor(h * dpr));
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };
        resize();
        const ro = new ResizeObserver(resize);
        if (canvas.parentElement)
            ro.observe(canvas.parentElement);
        const onMove = (e) => {
            const r = canvas.getBoundingClientRect();
            mouse.current.x = e.clientX - r.left;
            mouse.current.y = e.clientY - r.top;
            mouse.current.energy = Math.min(1, mouse.current.energy + 0.05);
        };
        addEventListener('pointermove', onMove, { passive: true });
        // Iridescent palette stops (hue wheel sample)
        const stops = [
            { h: 248, s: 92, l: 62 }, // indigo
            { h: 190, s: 95, l: 60 }, // cyan
            { h: 315, s: 88, l: 66 }, // magenta
            { h: 155, s: 80, l: 58 }, // teal-green
        ];
        const BANDS = 5;
        let raf = 0;
        const frame = (t) => {
            mouse.current.energy *= 0.96;
            ctx.clearRect(0, 0, w, h);
            const cx = w / 2;
            const cy = h * 0.5;
            for (let b = 0; b < BANDS; b++) {
                ctx.beginPath();
                const baseY = cy + (b - (BANDS - 1) / 2) * 30;
                const thick = 40 + b * 14 + mouse.current.energy * 22;
                const steps = 60;
                for (let s = 0; s <= steps; s++) {
                    const u = s / steps;
                    const x = u * w;
                    // 3 stacked sines, different frequencies/speeds
                    const dx = (x - mouse.current.x) / Math.max(1, w);
                    const dy = (baseY - mouse.current.y) / Math.max(1, h);
                    const d2 = dx * dx * 4 + dy * dy * 9;
                    const ripple = Math.exp(-d2 * 3.2) * mouse.current.energy * 34;
                    const y = baseY +
                        Math.sin(u * Math.PI * 1.6 + t * 0.00028 + b * 0.9) * 46 +
                        Math.sin(u * Math.PI * 3.4 - t * 0.00042 + b * 1.4) * 22 +
                        Math.sin(u * Math.PI * 6.2 + t * 0.0006 + b) * 8 +
                        ripple;
                    if (s === 0)
                        ctx.moveTo(x, y);
                    else
                        ctx.lineTo(x, y);
                }
                // hue drifts over time per band
                const stop = stops[b % stops.length];
                const hue = stop.h + Math.sin(t * 0.00012 + b) * 26;
                const grad = ctx.createLinearGradient(0, 0, w, 0);
                grad.addColorStop(0, `hsla(${hue}, ${stop.s}%, ${stop.l}%, 0)`);
                grad.addColorStop(0.5, `hsla(${hue}, ${stop.s}%, ${stop.l}%, ${0.28 + b * 0.04})`);
                grad.addColorStop(1, `hsla(${(hue + 40) % 360}, ${stop.s}%, ${stop.l}%, 0)`);
                ctx.strokeStyle = grad;
                ctx.lineWidth = thick;
                ctx.lineCap = 'round';
                ctx.stroke();
            }
            // Chrome sheen: faint light area above the ribbon core
            const sheen = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(w, h) * 0.42);
            sheen.addColorStop(0, 'rgba(196,181,253,0.06)');
            sheen.addColorStop(1, 'transparent');
            ctx.fillStyle = sheen;
            ctx.fillRect(0, 0, w, h);
            raf = requestAnimationFrame(frame);
        };
        raf = requestAnimationFrame(frame);
        return () => {
            cancelAnimationFrame(raf);
            ro.disconnect();
            removeEventListener('pointermove', onMove);
        };
    }, []);
    return <canvas ref={canvasRef} className={className} aria-hidden="true"/>;
};
export default LiquidRibbon;
