import React, { useEffect, useRef } from 'react';

/**
 * AuroraNebula — a fixed full-screen ambient field.
 * Two layered canvases are avoided: we mutate CSS variables consumed by body::before/after
 * (defined in index.css) plus one live canvas for the aurora ribons.
 */
const AuroraNebula: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const mouse = useRef({ x: 0.5, y: 0.5 });

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = 0;
    let h = 0;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const resize = () => {
      w = innerWidth;
      h = innerHeight;
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    addEventListener('resize', resize);

    const onMove = (e: PointerEvent) => {
      mouse.current.x = e.clientX / innerWidth;
      mouse.current.y = e.clientY / innerHeight;
    };
    addEventListener('pointermove', onMove, { passive: true });

    // Aurora ribbon parameters
    const RIBBONS = 5;
    const ribbon = Array.from({ length: RIBBONS }, (_, i) => ({
      hue: 250 - i * 14,
      amp: 40 + i * 44,
      speed: 0.00008 + i * 0.00004,
      phase: (i * Math.PI) / RIBBONS,
      thick: 90 + i * 60,
    }));

    let raf = 0;
    const frame = (t: number) => {
      ctx.clearRect(0, 0, w, h);
      const cx = w * (0.5 + (mouse.current.x - 0.5) * 0.12);
      const cy = h * (0.42 + (mouse.current.y - 0.5) * 0.08);

      // diffuse radial glow following pointer area
      const g = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(w, h) * 0.7);
      g.addColorStop(0, 'rgba(99,102,241,0.10)');
      g.addColorStop(0.5, 'rgba(139,92,246,0.05)');
      g.addColorStop(1, 'transparent');
      ctx.fillStyle = g;
      ctx.fillRect(0, 0, w, h);

      // aurora ribbons
      for (const r of ribbon) {
        ctx.beginPath();
        const baseY = h * 0.28 + Math.sin(t * r.speed + r.phase) * 20;
        const steps = 40;
        for (let s = 0; s <= steps; s++) {
          const x = (s / steps) * w;
          const y =
            baseY +
            Math.sin(s * 0.14 + t * r.speed * 2 + r.phase) * r.amp * Math.sin((s / steps) * Math.PI) +
            Math.sin(s * 0.05 + t * r.speed * 3) * 12;
          if (s === 0) ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
        }
        ctx.lineWidth = r.thick;
        ctx.strokeStyle = `hsla(${r.hue}, 85%, 62%, ${0.035 + Math.abs(Math.sin(t * r.speed * 5 + r.phase)) * 0.04})`;
        ctx.filter = 'blur(28px)';
        ctx.stroke();
        ctx.filter = 'none';
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      removeEventListener('resize', resize);
      removeEventListener('pointermove', onMove);
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 z-0 pointer-events-none opacity-80"
      aria-hidden="true"
    />
  );
};

export default AuroraNebula;
