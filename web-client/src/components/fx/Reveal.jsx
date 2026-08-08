import React, { useEffect, useRef, useState } from 'react';
/** Fade-and-rise entrance when scrolled into view (fires once). */
const Reveal = ({ children, className = '', delay = 0, as = 'div' }) => {
    const ref = useRef(null);
    const [visible, setVisible] = useState(false);
    useEffect(() => {
        const el = ref.current;
        if (!el)
            return;
        const timer = setTimeout(() => setVisible(true), 500);
        const io = new IntersectionObserver((entries) => {
            if (entries[0].isIntersecting) {
                setVisible(true);
                clearTimeout(timer);
                io.disconnect();
            }
        }, { threshold: 0.01 });
        io.observe(el);
        return () => {
            clearTimeout(timer);
            io.disconnect();
        };
    }, []);
    const Tag = as;
    return (<Tag ref={ref} style={{ transitionDelay: `${delay}ms` }} className={`${className} transition-all duration-700 ease-out will-change-transform ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}>
      {children}
    </Tag>);
};
export default Reveal;
