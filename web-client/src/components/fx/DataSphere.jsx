import React, { useEffect, useRef } from 'react';
const GOLDEN = Math.PI * (3 - Math.sqrt(5));
const DataSphere = ({ className, points = 320, lineColor = '129,140,248', pointColor = '165,180,252', spin = 0.00022, }) => {
    const canvasRef = useRef(null);
    const mouse = useRef({ x: 0, y: 0 });
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas)
            return;
        const ctx = canvas.getContext('2d');
        if (!ctx)
            return;
        // Fibonacci sphere lattice
        const base = [];
        for (let i = 0; i < points; i++) {
            const y = 1 - (i / (points - 1)) * 2;
            const r = Math.sqrt(1 - y * y);
            const theta = GOLDEN * i;
            base.push([Math.cos(theta) * r, y, Math.sin(theta) * r]);
        }
        // Lattice-neighbor edges: spiral neighbors (i,i+1) and cross-latitude (i,i+k)
        const k = Math.max(8, Math.round(Math.sqrt(points)));
        const edges = [];
        for (let i = 0; i < points; i++) {
            edges.push([i, (i + 1) % points]);
            const j = i + k;
            if (j < points)
                edges.push([i, j]);
        }
        let raf = 0;
        let w = 0;
        let h = 0;
        const resize = () => {
            const dpr = Math.min(window.devicePixelRatio || 1, 2);
            w = canvas.clientWidth;
            h = canvas.clientHeight;
            canvas.width = Math.max(1, Math.floor(w * dpr));
            canvas.height = Math.max(1, Math.floor(h * dpr));
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        };
        resize();
        const ro = new ResizeObserver(resize);
        ro.observe(canvas);
        const onMove = (e) => {
            const rect = canvas.getBoundingClientRect();
            mouse.current.x = ((e.clientX - rect.left) / Math.max(rect.width, 1)) * 2 - 1;
            mouse.current.y = ((e.clientY - rect.top) / Math.max(rect.height, 1)) * 2 - 1;
        };
        window.addEventListener('pointermove', onMove, { passive: true });
        const rotated = new Float32Array(points * 3);
        const frame = (t) => {
            const ry = t * spin;
            const rx = 0.35 + mouse.current.y * 0.25;
            const tz = mouse.current.x * 0.35;
            const cy = Math.cos(ry + tz);
            const sy = Math.sin(ry + tz);
            const cx = Math.cos(rx);
            const sx = Math.sin(rx);
            for (let i = 0; i < points; i++) {
                const [x0, y0, z0] = base[i];
                // rotate around Y then X
                const x1 = x0 * cy + z0 * sy;
                const z1 = -x0 * sy + z0 * cy;
                const y2 = y0 * cx - z1 * sx;
                const z2 = y0 * sx + z1 * cx;
                rotated[i * 3] = x1;
                rotated[i * 3 + 1] = y2;
                rotated[i * 3 + 2] = z2;
            }
            ctx.clearRect(0, 0, w, h);
            const R = Math.min(w, h) * 0.36;
            const cX = w / 2;
            const cY = h / 2;
            const fov = 2.6;
            // edges
            ctx.lineWidth = 1;
            for (let e = 0; e < edges.length; e++) {
                const a = edges[e][0] * 3;
                const b = edges[e][1] * 3;
                const za = rotated[a + 2];
                const zb = rotated[b + 2];
                const depth = (za + zb) / 2; // -1..1
                if (depth < -0.15)
                    continue; // skip far-side edges
                const pa = fov / (fov - za);
                const pb = fov / (fov - zb);
                const alpha = 0.05 + Math.max(0, depth) * 0.22;
                ctx.strokeStyle = `rgba(${lineColor},${alpha.toFixed(3)})`;
                ctx.beginPath();
                ctx.moveTo(cX + rotated[a] * R * pa, cY - rotated[a + 1] * R * pa);
                ctx.lineTo(cX + rotated[b] * R * pb, cY - rotated[b + 1] * R * pb);
                ctx.stroke();
            }
            // points
            for (let i = 0; i < points; i++) {
                const x = rotated[i * 3];
                const y = rotated[i * 3 + 1];
                const z = rotated[i * 3 + 2];
                const p = fov / (fov - z);
                const front = Math.max(0, z);
                const size = 1.1 + front * 1.7;
                const alpha = 0.25 + front * 0.65;
                ctx.fillStyle = `rgba(${pointColor},${alpha.toFixed(3)})`;
                ctx.beginPath();
                ctx.arc(cX + x * R * p, cY - y * R * p, size * p, 0, Math.PI * 2);
                ctx.fill();
                if (front > 0.85) {
                    ctx.fillStyle = `rgba(${pointColor},0.08)`;
                    ctx.beginPath();
                    ctx.arc(cX + x * R * p, cY - y * R * p, size * p * 3.4, 0, Math.PI * 2);
                    ctx.fill();
                }
            }
            raf = requestAnimationFrame(frame);
        };
        raf = requestAnimationFrame(frame);
        return () => {
            cancelAnimationFrame(raf);
            ro.disconnect();
            window.removeEventListener('pointermove', onMove);
        };
    }, [points, lineColor, pointColor, spin]);
    return <canvas ref={canvasRef} className={className} aria-hidden="true"/>;
};
export default DataSphere;
