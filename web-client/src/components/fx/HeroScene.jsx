/**
 * Hero 3D scene — WebGL. Bright particle sphere with bloom-cheap additive blending.
 * Falls back to the DataSphere 2D canvas engine if WebGL is unavailable.
 */
import React, { useEffect, useRef, useState } from 'react';
import DataSphere from './DataSphere';
const VERT = `
attribute vec3 aPos;
attribute float aSeed;
uniform mat4 uMVP;
uniform float uPointScale;
varying float vSeed;
varying float vDepth;
void main() {
  vSeed = aSeed;
  vec4 world = uMVP * vec4(aPos, 1.0);
  vDepth = world.z;
  gl_Position = world;
  gl_PointSize = uPointScale * (1.6 + 0.8*sin(aSeed*25.0) + world.z*0.9);
}`;
const FRAG = `
precision mediump float;
varying float vSeed;
varying float vDepth;
void main() {
  vec2 uv = gl_PointCoord - 0.5;
  float d = length(uv);
  if (d > 0.5) discard;
  float alpha = smoothstep(0.5, 0.0, d);
  alpha *= 0.75 + 0.45 * sin(vSeed * 311.0);
  alpha *= 0.5 + 0.5 * vDepth; // brighter when coming forward
  vec3 col = mix(vec3(0.55, 0.62, 1.0), vec3(0.35, 0.9, 1.0), fract(vSeed * 5.0));
  col = mix(col, vec3(0.7, 0.55, 1.0), sin(vSeed * 13.7) * 0.5 + 0.5);
  gl_FragColor = vec4(col, alpha * 0.85);
}`;
function buildSphere(count) {
    const GOLDEN = Math.PI * (3 - Math.sqrt(5));
    const pos = new Float32Array(count * 3);
    const seed = new Float32Array(count);
    for (let i = 0; i < count; i++) {
        const y = 1 - (i / (count - 1)) * 2;
        const r = Math.sqrt(1 - y * y);
        const th = GOLDEN * i;
        pos[i * 3] = Math.cos(th) * r;
        pos[i * 3 + 1] = y;
        pos[i * 3 + 2] = Math.sin(th) * r;
        seed[i] = Math.random();
    }
    return { pos, seed, count };
}
const HeroScene = ({ className }) => {
    const mountRef = useRef(null);
    const [webgl] = useState(() => {
        try {
            const c = document.createElement('canvas');
            return !!(c.getContext('webgl2') || c.getContext('webgl'));
        }
        catch {
            return false;
        }
    });
    useEffect(() => {
        if (!webgl || !mountRef.current)
            return;
        const mount = mountRef.current;
        const canvas = document.createElement('canvas');
        canvas.style.position = 'absolute';
        canvas.style.inset = '0';
        canvas.style.width = '100%';
        canvas.style.height = '100%';
        mount.appendChild(canvas);
        const gl = (canvas.getContext('webgl2') ||
            canvas.getContext('webgl'));
        if (!gl)
            return;
        const compile = (type, src) => {
            const s = gl.createShader(type);
            gl.shaderSource(s, src);
            gl.compileShader(s);
            if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
                console.warn('shader', gl.getShaderInfoLog(s));
            }
            return s;
        };
        const prog = gl.createProgram();
        gl.attachShader(prog, compile(gl.VERTEX_SHADER, VERT));
        gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FRAG));
        gl.linkProgram(prog);
        if (!gl.getProgramParameter(prog, gl.LINK_STATUS))
            return;
        gl.useProgram(prog);
        const { pos, seed, count } = buildSphere(1800);
        const vboPos = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, vboPos);
        gl.bufferData(gl.ARRAY_BUFFER, pos, gl.STATIC_DRAW);
        const aPos = gl.getAttribLocation(prog, 'aPos');
        gl.enableVertexAttribArray(aPos);
        gl.vertexAttribPointer(aPos, 3, gl.FLOAT, false, 0, 0);
        const vboSeed = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, vboSeed);
        gl.bufferData(gl.ARRAY_BUFFER, seed, gl.STATIC_DRAW);
        const aSeed = gl.getAttribLocation(prog, 'aSeed');
        gl.enableVertexAttribArray(aSeed);
        gl.vertexAttribPointer(aSeed, 1, gl.FLOAT, false, 0, 0);
        const uMVP = gl.getUniformLocation(prog, 'uMVP');
        const uPointScale = gl.getUniformLocation(prog, 'uPointScale');
        let raf = 0;
        let w = 0;
        let h = 0;
        const dpr = Math.min(devicePixelRatio || 1, 2);
        const resize = () => {
            w = mount.clientWidth;
            h = mount.clientHeight;
            canvas.width = Math.max(1, Math.floor(w * dpr));
            canvas.height = Math.max(1, Math.floor(h * dpr));
            gl.viewport(0, 0, canvas.width, canvas.height);
        };
        resize();
        const ro = new ResizeObserver(resize);
        ro.observe(mount);
        const frame = (t) => {
            const a = t * 0.00016;
            const b = 0.42;
            // mat4 column-major helper matrices
            const aspect = w / Math.max(h, 1);
            const fov = Math.PI / 3.8; // slightly wide for drama
            const f = 1 / Math.tan(fov / 2);
            const near = 0.1;
            const far = 12.0;
            const ca = Math.cos(a);
            const sa = Math.sin(a);
            const cb = Math.cos(b);
            const sb = Math.sin(b);
            // Rotation world = Ry(a) * Rx(b)
            // perspective matrix
            const P = new Float32Array(16);
            P[0] = f / aspect;
            P[1] = 0;
            P[2] = 0;
            P[3] = 0;
            P[4] = 0;
            P[5] = f;
            P[6] = 0;
            P[7] = 0;
            P[8] = 0;
            P[9] = 0;
            P[10] = (far + near) / (near - far);
            P[11] = -1;
            P[12] = 0;
            P[13] = 0;
            P[14] = (2 * far * near) / (near - far);
            P[15] = 0;
            // View: translate(0,0,-3.2) * Ry(a) * Rx(b)
            const R = new Float32Array(16);
            R[0] = ca;
            R[1] = sb * sa;
            R[2] = cb * sa;
            R[4] = 0;
            R[5] = cb;
            R[6] = -sb;
            R[8] = -sa;
            R[9] = sb * ca;
            R[10] = cb * ca;
            R[15] = 1;
            R[14] = -3.35;
            // MVP = P * R
            const m = new Float32Array(16);
            for (let i = 0; i < 4; i++) {
                for (let j = 0; j < 4; j++) {
                    m[j * 4 + i] =
                        P[i] * R[j * 4] +
                            P[4 + i] * R[j * 4 + 1] +
                            P[8 + i] * R[j * 4 + 2] +
                            P[12 + i] * R[j * 4 + 3];
                }
            }
            gl.clearColor(0, 0, 0, 0);
            gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
            gl.disable(gl.DEPTH_TEST);
            gl.enable(gl.BLEND);
            gl.blendFunc(gl.SRC_ALPHA, gl.ONE); // additive pop
            gl.uniformMatrix4fv(uMVP, false, m);
            gl.uniform1f(uPointScale, Math.max(3, (w / 240) * dpr));
            gl.drawArrays(gl.POINTS, 0, count);
            raf = requestAnimationFrame(frame);
        };
        raf = requestAnimationFrame(frame);
        return () => {
            cancelAnimationFrame(raf);
            ro.disconnect();
            gl.deleteBuffer(vboPos);
            gl.deleteBuffer(vboSeed);
            gl.deleteProgram(prog);
            if (canvas.parentNode === mount)
                mount.removeChild(canvas);
        };
    }, [webgl]);
    if (webgl) {
        return <div ref={mountRef} className={className} aria-hidden="true"/>;
    }
    return <DataSphere className={className} points={560}/>;
};
export default HeroScene;
