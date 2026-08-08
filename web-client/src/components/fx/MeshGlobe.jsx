import React, { useEffect, useRef } from 'react';
const MeshGlobe = ({ className = '', nodes = 420 }) => {
    const canvasRef = useRef(null);
    const mouse = useRef({ x: 0, y: 0 });
    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas)
            return;
        const ctx = canvas.getContext('2d');
        if (!ctx)
            return;
        const GOLDEN = Math.PI * (3 - Math.sqrt(5));
        const pts = [];
        for (let i = 0; i < nodes; i++) {
            const y = 1 - (i / (nodes - 1)) * 2;
            const r = Math.sqrt(1 - y * y);
            const th = GOLDEN * i;
            pts.push([Math.cos(th) * r, y, Math.sin(th) * r]);
        }
        const k = Math.max(6, Math.round(Math.sqrt(nodes)));
        const edges = [];
        for (let i = 0; i < nodes; i++) {
            edges.push([i, (i + 1) % nodes]);
            const j = i + k;
            if (j < nodes)
                edges.push([i, j]);
        }
        let raf = 0;
        let w = 0;
        let h = 0;
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const resize = () => {
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
            mouse.current.x = e.clientX / innerWidth - 0.5;
            mouse.current.y = e.clientY / innerHeight - 0.5;
        };
        addEventListener('pointermove', onMove, { passive: true });
        const rotated = new Float32Array(nodes * 3);
        let links = [];
        const spawnLink = () => {
            const a = Math.floor(Math.random() * nodes);
            let b = (a + k) % nodes;
            while (Math.abs(b - a) < 4)
                b = Math.floor(Math.random() * nodes);
            links.push({ a, b, t: 0, life: 1, dur: 0.8 + Math.random() * 1.6 });
        };
        const frame = (t) => {
            const ry = t * 0.00014 + mouse.current.x * 0.4;
            const rx = 0.36 + mouse.current.y * 0.22;
            const cy = Math.cos(ry);
            const sy = Math.sin(ry);
            const cx = Math.cos(rx);
            const sx = Math.sin(rx);
            for (let i = 0; i < nodes; i++) {
                const [x0, y0, z0] = pts[i];
                const x1 = x0 * cy + z0 * sy;
                const z1 = -x0 * sy + z0 * cy;
                const y2 = y0 * cx - z1 * sx;
                const z2 = y0 * sx + z1 * cx;
                rotated[i * 3] = x1;
                rotated[i * 3 + 1] = y2;
                rotated[i * 3 + 2] = z2;
            }
            ctx.clearRect(0, 0, w, h);
            const R = Math.min(w, h) * 0.34;
            const cxp = w / 2;
            const cyp = h / 2;
            const fov = 2.6;
            // faint grid-ish edges
            ctx.lineWidth = 1;
            for (const [a, b] of edges) {
                const za = rotated[a * 3 + 2];
                const zb = rotated[b * 3 + 2];
                const depth = (za + zb) / 2;
                if (depth < -0.35)
                    continue;
                const pa = fov / (fov - za);
                const pb = fov / (fov - zb);
                const alpha = 0.04 + Math.max(0, depth) * 0.18;
                ctx.strokeStyle = `rgba(148,163,255,${alpha.toFixed(3)})`;
                ctx.beginPath();
                ctx.moveTo(cxp + rotated[a * 3] * R * pa, cyp - rotated[a * 3 + 1] * R * pa);
                ctx.lineTo(cxp + rotated[b * 3] * R * pb, cyp - rotated[b * 3 + 1] * R * pb);
                ctx.stroke();
            }
            // node dots — teal, brighter forward
            for (let i = 0; i < nodes; i++) {
                const x = rotated[i * 3];
                const y = rotated[i * 3 + 1];
                const z = rotated[i * 3 + 2];
                const p = fov / (fov - z);
                const front = Math.max(0, z);
                const size = 0.8 + front * 1.6;
                const alpha = 0.2 + front * 0.7;
                ctx.fillStyle = `rgba(103,232,249,${alpha.toFixed(3)})`;
                ctx.beginPath();
                ctx.arc(cxp + x * R * p, cyp - y * R * p, size * p, 0, Math.PI * 2);
                ctx.fill();
            }
            // Launch arcs
            if (links.length < 4 && Math.random() < 0.03)
                spawnLink();
            links = links.filter((l) => l.life > 0);
            for (const l of links) {
                l.t += 1 / (60 * l.dur);
                l.life -= 0.006;
                const A = l.a * 3;
                const B = l.b * 3;
                const ax = rotated[A];
                const ay = rotated[A + 1];
                const az = rotated[A + 2];
                const bx = rotated[B];
                const by = rotated[B + 1];
                const bz = rotated[B + 2];
                // Quadratic bezier in 2D after projection of endpoints, with humpp toward viewer
                const midX = (ax + bx) / 2;
                const midY = (ay + by) / 2;
                const bend = 0.3 + Math.min(0.3, Math.hypot(midX, midY) * 0.3);
                const mxp = midX;
                const myp = midY - bend;
                ctx.beginPath();
                ctx.strokeStyle = `rgba(52,211,153,${(0.55 * l.life).toFixed(3)})`;
                ctx.lineWidth = 1.6;
                ctx.setLineDash([6, 6]);
                ctx.moveTo(cxp + ax * R * (fov / (fov - az)), cyp - ay * R * (fov / (fov - az)));
                ctx.quadraticCurveTo(cxp + mxp * R * (fov / (fov - 0.05)), cyp - myp * R * (fov / (fov - 0.05)), cxp + bx * R * (fov / (fov - bz)), cyp - by * R * (fov / (fov - bz)));
                ctx.stroke();
                ctx.setLineDash([]);
                // bright head dot
                const headX = cxp +
                    (ax + (mxp - ax) * l.t + (bx - mxp) * l.t * l.t) * R * (fov / (fov - (az + (0.05 - az) * l.t)));
                const headY = cyp -
                    (ay + (myp - ay) * l.t + (by - myp) * l.t * l.t) * R * (fov / (fov - (az + (0.05 - az) * l.t)));
                ctx.fillStyle = `rgba(52,211,153,${(0.9 * l.life).toFixed(3)})`;
                ctx.beginPath();
                ctx.arc(headX, headY, 2.6 * l.life, 0, Math.PI * 2);
                ctx.fill();
            }
            raf = requestAnimationFrame(frame);
        };
        raf = requestAnimationFrame(frame);
        return () => {
            cancelAnimationFrame(raf);
            ro.disconnect();
            removeEventListener('pointermove', onMove);
        };
    }, [nodes]);
    return <canvas ref={canvasRef} className={className} aria-hidden="true"/>;
};
export default MeshGlobe;
