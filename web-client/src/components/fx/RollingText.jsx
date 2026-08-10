import React, { useEffect, useRef } from 'react';
/**
 * Kinetic headline: word list vertically rolls (y-flip) with a cubic snap,
 * each word riding a gradient. Sibling of the static gradient span.
 */
const RollingText = ({ words, className = '', interval = 2600 }) => {
    const [idx, setIdx] = React.useState(0);
    const tRef = useRef(undefined);
    useEffect(() => {
        tRef.current = window.setInterval(() => {
            setIdx((i) => (i + 1) % words.length);
        }, interval);
        return () => clearInterval(tRef.current);
    }, [words.length, interval]);
    return (<span className={`relative inline-block overflow-hidden align-bottom ${className}`} style={{ verticalAlign: 'bottom' }}>
          <span className="invisible">{words[0]}</span>
      {words.map((word, i) => {
            const active = i === idx;
            const prev = (idx - 1 + words.length) % words.length === i;
            return (<span key={word} className="absolute left-0 top-0 whitespace-nowrap bg-clip-text text-transparent bg-linear-to-r from-indigo-400 via-violet-400 to-cyan-300" style={{
                    transform: active ? 'translateY(0)' : prev ? 'translateY(-110%)' : 'translateY(110%)',
                    opacity: active ? 1 : 0,
                    transition: 'transform 0.6s cubic-bezier(0.76, 0, 0.24, 1), opacity 0.4s',
                }}>
          {word}
          </span>);
        })}
    </span>);
};
export default RollingText;
