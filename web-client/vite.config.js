import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// This bundle is deployed to two places that disagree about where it lives.
//
// GitHub Pages serves it from /Decentralized-Network/ (a project page is always
// under the repository name). Vercel serves it from the domain root. Building
// with the wrong base is not a visible error -- index.html loads, every asset
// 404s, and the page renders blank with nothing naming the cause.
//
// VERCEL is set by Vercel's own build environment, so this needs no
// configuration in either place.
const base = process.env.VERCEL ? '/' : '/Decentralized-Network/';

export default defineConfig({
    base,
    plugins: [react()],
    server: {
        port: 3000,
    },
});
