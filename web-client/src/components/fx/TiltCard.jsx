import React, { useRef } from 'react';
/** CSS-3D tilt-on-hover card with optional moving glare highlight. */
const TiltCard = ({ children, className = '', max = 10, glare = true }) => {
    const ref = useRef(null);
    const onMove = (e) => {
        const el = ref.current;
        if (!el || e.pointerType === 'touch')
            return;
        const r = el.getBoundingClientRect();
        const px = (e.clientX - r.left) / r.width - 0.5;
        const py = (e.clientY - r.top) / r.height - 0.5;
        el.style.transform = `rotateX(${(-py * max).toFixed(2)}deg) rotateY(${(px * max).toFixed(2)}deg) translateZ(0)`;
        el.style.setProperty('--glare-x', `${((px + 0.5) * 100).toFixed(1)}%`);
        el.style.setProperty('--glare-y', `${((py + 0.5) * 100).toFixed(1)}%`);
    };
    const onLeave = () => {
        const el = ref.current;
        if (!el)
            return;
        el.style.transform = 'rotateX(0deg) rotateY(0deg)';
    };
    return (<div className="perspective-1200">
      <div ref={ref} onPointerMove={onMove} onPointerLeave={onLeave} className={`preserve-3d relative transition-transform duration-200 ease-out will-change-transform ${className}`}>
        {children}
        {glare && (<div className="pointer-events-none absolute inset-0 rounded-[inherit] opacity-0 group-hover:opacity-100 transition-opacity duration-300" style={{
                background: 'radial-gradient(320px circle at var(--glare-x,50%) var(--glare-y,50%), rgba(165,180,252,0.14), transparent 60%)',
            }}/>)}
      </div>
    </div>);
};
export default TiltCard;
