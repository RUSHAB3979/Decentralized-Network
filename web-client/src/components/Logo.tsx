import React from 'react';

/**
 * Mark — a compressed forge anvil / hex node glyph.
 * Inline so it inherits currentColor and keeps the bundle dependency-free.
 */
const Logo: React.FC<{ className?: string }> = ({ className = '' }) => (
  <svg
    viewBox="0 0 32 32"
    className={className}
    fill="none"
    aria-hidden="true"
    role="img"
  >
    <defs>
      <linearGradient id="lg" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stopColor="#a5b4fc" />
        <stop offset="100%" stopColor="#8b5cf6" />
      </linearGradient>
    </defs>
    {/* outer hex */}
    <path
      d="M16 2.5 28.4 9.25v13.5L16 29.5 3.6 22.75V9.25L16 2.5Z"
      stroke="url(#lg)"
      strokeWidth="1.6"
      strokeLinejoin="round"
    />
    {/* inner node cluster */}
    <circle cx="16" cy="16" r="3.2" fill="url(#lg)" opacity="0.9" />
    <circle cx="16" cy="9.4" r="1.5" fill="#a5b4fc" opacity="0.8" />
    <circle cx="9.4" cy="16" r="1.5" fill="#a5b4fc" opacity="0.8" />
    <circle cx="22.6" cy="16" r="1.5" fill="#a5b4fc" opacity="0.8" />
    <circle cx="16" cy="22.6" r="1.5" fill="#a5b4fc" opacity="0.8" />
    <path d="M16 12.8v-3.4M16 19.2v3.4M12.8 16H9.4M19.2 16h3.4" stroke="url(#lg)" strokeWidth="1.1" opacity="0.7" />
  </svg>
);

export default Logo;
