import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Separate build from vite.config.js because the desktop window and the public
// site disagree on two things that cannot both be true in one config.
//
//  - base: the site is served from a GitHub Pages subpath, the window is loaded
//    from a file:// URL. Absolute asset paths resolve to the filesystem root
//    there and 404 silently, leaving a blank window with no error.
//  - output: the desktop bundle has to land inside agent/, because PyInstaller
//    packages the exe from that tree.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: {
    rollupOptions: { input: 'desktop.html' },
    outDir: '../agent/ui/web',
    emptyOutDir: true,
    // One file each. A desktop window loading from disk gains nothing from
    // code splitting and it makes the PyInstaller data spec harder to reason
    // about.
    assetsInlineLimit: 0,
  },
});
