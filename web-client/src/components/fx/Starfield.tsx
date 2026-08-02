import React, { useEffect, useRef } from 'react';

/** Layered drifting starfield + nebula glow, pointer-parallax. */
const Starfield: React.FC<{ className?: string; density?: number }> = ({
  className,
  density = 0.00018,
}) => {
  const ref = useRef<HTMLCanvasElement>(null);
  const mouse = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let w = 0;
    let h = 0;
    let stars: Array<{ x: number; y: number; z: number; r: number; tw: number }> = [];

    const build = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.max(1, Math.floor(w * dpr));
      canvas.height = Math.max(1, Math.floor(h * dpr));
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const count = Math.floor(w * h * density);
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        z: 0.25 + Math.random() * 0.75,
        r: 0.4 + Math.random() * 1.4,
        tw: Math.random() * Math.PI * 2,
      }));
    };
    build();
    const ro = new ResizeObserver(build);
    ro.observe(canvas);

    const onMove = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouse.current.x = ((e.clientX - rect.left) / Math.max(rect.width, 1)) * 2 - 1;
      mouse.current.y = ((e.clientY - rect.top) / Math.max(rect.height, 1)) * 2 - 1;
    };
    window.addEventListener('pointermove', onMove, { passive: true });

    let raf = 0;
    const frame = (t: number) => {
      ctx.clearRect(0, 0, w, h);
      for (const s of stars) {
        const px = s.x - mouse.current.x * 18 * s.z;
        const py = (s.y - mouse.current.y * 12 * s.z + t * 0.006 * s.z) % h;
        const y = py < 0 ? py + h : py;
        const a = 0.25 + 0.45 * s.z * (0.6 + 0.4 * Math.sin(t * 0.001 + s.tw));
        ctx.fillStyle = `rgba(199,210,254,${a.toFixed(3)})`;
        ctx.beginPath();
        ctx.arc(px, y, s.r * s.z, 0, Math.PI * 2);
        ctx.fill();
      }
      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
      window.removeEventListener('pointermove', onMove);
    };
  }, [density]);

  return <canvas ref={ref} className={className} aria-hidden="true" />;
};

export default Starfield;
