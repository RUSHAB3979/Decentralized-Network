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

// Everywhere this bundle is allowed to talk to.
//
// The session token lives in localStorage, which is a deliberate trade (see
// services/authApi.js) and one whose cost is entirely paid by script injection:
// any script that runs on this origin can read it. So the defence that matters
// is not moving the token, it is making sure injected script cannot run at all
// and cannot reach anywhere if it does.
//
// The hosted orchestrator is listed by name rather than covered by a wildcard.
// A wildcard would let an injected script post a stolen token to an attacker's
// subdomain, which is most of the value of exfiltration.
const API_ORIGINS = [
    'https://decentralized-network.onrender.com',
    // Development. The dev server runs on a different port from the API, so
    // 'self' does not cover it, and omitting these breaks `npm run dev` with a
    // console error that reads like the backend is down.
    'http://localhost:8080',
    'http://127.0.0.1:8080',
];

if (process.env.VITE_ORCHESTRATOR_URL) {
    // A deployment pointed at its own backend has to be able to reach it. This
    // is read at build time from the same variable services/api.js reads at
    // run time, so the two cannot drift into a policy that blocks every request
    // the app makes.
    try {
        API_ORIGINS.push(new URL(process.env.VITE_ORCHESTRATOR_URL).origin);
    }
    catch {
        throw new Error(
            `VITE_ORCHESTRATOR_URL is not a valid URL: ${process.env.VITE_ORCHESTRATOR_URL}. `
            + 'Refusing to build a bundle whose content policy would block every API call.',
        );
    }
}

const CSP = [
    "default-src 'self'",
    // No 'unsafe-inline' and no 'unsafe-eval'. This is the directive that does
    // the work: with it, an injected <script> or a javascript: URL does not
    // execute, so the token in localStorage is not reachable in the first place.
    "script-src 'self'",
    // Styles keep 'unsafe-inline' because React sets style attributes and
    // Tailwind's runtime injects a stylesheet. Inline CSS cannot read
    // localStorage or issue a request, so this is a much smaller allowance than
    // it looks -- it is not the same concession as inline script.
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    'font-src \'self\' https://fonts.gstatic.com',
    "img-src 'self' data: blob:",
    `connect-src 'self' ${API_ORIGINS.join(' ')}`,
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    // Ignored when it arrives in a <meta> tag -- frame-ancestors only works as
    // a real response header, which neither GitHub Pages nor a plain static
    // host lets us set. It is listed anyway so that moving to a host that does
    // send headers is a copy rather than a rediscovery, and so the omission is
    // visible here instead of being silently absent.
    "frame-ancestors 'none'",
].join('; ');

// Injected immediately after <meta charset>, not before it. A meta policy only
// governs what the parser reaches after it, so it has to come before the font
// <link> and before the script tag Vite adds -- but the character encoding
// declaration has to stay inside the document's first 1024 bytes or the browser
// falls back to guessing, and the policy is long enough to push it out. Placing
// it by anchor rather than by injectTo: 'head-prepend' satisfies both.
const CHARSET = /(<meta\s+charset=["']?[^>]*>)/i;

const SECURITY_META = [
    `<meta http-equiv="Content-Security-Policy" content="${CSP}" />`,
    // Stops a response whose Content-Type is wrong from being executed as
    // something more dangerous than it was served as.
    '<meta http-equiv="X-Content-Type-Options" content="nosniff" />',
    // Console URLs carry job and node identifiers. Sending them to
    // fonts.googleapis.com in a Referer header leaks customer structure for no
    // benefit.
    '<meta name="referrer" content="strict-origin-when-cross-origin" />',
].join('\n    ');

/** Put the policy in the built page, and in the dev server's page. */
function contentSecurityPolicy() {
    return {
        name: 'content-security-policy',
        transformIndexHtml(html) {
            if (!CHARSET.test(html)) {
                // Failing the build is the right response. Silently returning
                // the page unchanged would ship a bundle with no policy at all,
                // and the only way to notice would be to read the deployed
                // HTML.
                throw new Error(
                    'index.html has no <meta charset>, so the security headers have '
                    + 'nowhere safe to be inserted. Add it back before building.',
                );
            }
            return html.replace(CHARSET, `$1\n    ${SECURITY_META}`);
        },
    };
}

export default defineConfig({
    base,
    plugins: [react(), contentSecurityPolicy()],
    build: {
        // Vite otherwise inlines a small module-preload polyfill directly into
        // index.html, and an inline <script> is exactly what script-src 'self'
        // refuses -- the page would load and then execute nothing, which looks
        // like a blank white deployment. The polyfill only matters for browsers
        // without modulepreload support; every browser that can run this app's
        // ES modules at all has had it for years.
        modulePreload: { polyfill: false },
    },
    server: {
        port: 3000,
    },
});
