import React from 'react';

/** Film grain — a static SVG-noise tile + vignette layered over everything. Cheap, always-on. */
const FilmGrain: React.FC = () => (
  <div className="pointer-events-none fixed inset-0 z-[70]" aria-hidden="true">
    <div className="absolute inset-0 opacity-[0.05] mix-blend-overlay"
      style={{
        backgroundImage:
          'url("data:image/svg+xml;utf8,<svg xmlns=%22http://www.w3.org/2000/svg%22 width=%22180%22 height=%22180%22><filter id=%22n%22><feTurbulence type=%22fractalNoise%22 baseFrequency=%220.9%22 numOctaves=%222%22 stitchTiles=%22stitch%22/><feColorMatrix type=%22saturate%22 values=%220%22/></filter><rect width=%22180%22 height=%22180%22 filter=%22url(%23n)%22 opacity=%220.9%22/></svg>")',
      }}
    />
    <div className="absolute inset-0"
      style={{
        background: 'radial-gradient(ellipse 90% 90% at 50% 40%, transparent 55%, rgba(2,6,23,0.55) 100%)',
      }}
    />
  </div>
);

export default FilmGrain;
