import React from 'react';
/** GPUOrbit: linked compute core and orbiting provider nodes. */
const Logo = ({ className = '' }) => (
  <svg viewBox="0 0 40 40" className={className} fill="none" aria-hidden="true">
    <ellipse cx="20" cy="20" rx="17" ry="8.3" transform="rotate(-38 20 20)" stroke="#67e8f9" strokeWidth="1.8"/>
    <ellipse cx="20" cy="20" rx="17" ry="8.3" transform="rotate(38 20 20)" stroke="#a78bfa" strokeWidth="1.3"/>
    <rect x="15" y="15" width="10" height="10" rx="2" fill="#080e21" stroke="#67e8f9" strokeWidth="1.6"/>
    <circle cx="6.5" cy="27.6" r="2.2" fill="#67e8f9"/>
    <circle cx="31.9" cy="10.8" r="2.2" fill="#a78bfa"/>
  </svg>
);
export default Logo;
