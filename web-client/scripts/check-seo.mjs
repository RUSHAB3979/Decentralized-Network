// Phase 1 SEO checks run after Vite builds the public site.
// Keep the single-page sitemap truthful until distinct public pages exist.
import { readFileSync } from 'node:fs';

const read = (file) => readFileSync(new URL(`../dist/${file}`, import.meta.url), 'utf8');
const html = read('index.html');
const robots = read('robots.txt');
const sitemap = read('sitemap.xml');

const assert = (ok, message) => {
  if (!ok) throw new Error(`SEO check failed: ${message}`);
};

assert(/<title>GPUOrbit\s*\|\s*Peer-to-Peer GPU Compute Marketplace/i.test(html), 'homepage title');
assert(/<meta\s+name="description"\s+content="[^"]*public GPU rentals are not yet live\."/i.test(html), 'honest MVP description');
assert(/<link\s+rel="canonical"\s+href="https:\/\/gpuorbit\.dev\/"\s*\/>/i.test(html), 'canonical URL');
assert(/<meta\s+name="robots"\s+content="index, follow, max-image-preview:large"/i.test(html), 'indexability metadata');
assert(/<meta\s+property="og:url"\s+content="https:\/\/gpuorbit\.dev\/"\s*\/>/i.test(html), 'Open Graph URL');
assert(/<meta\s+name="twitter:card"\s+content="summary"/i.test(html), 'Twitter card metadata');
assert(html.includes('Content-Security-Policy'), 'existing CSP retained');

const structuredData = html.match(/<script\s+type="application\/ld\+json"\s*>([\s\S]*?)<\/script>/i);
assert(structuredData, 'schema.org JSON-LD');
const website = JSON.parse(structuredData[1]);
assert(website['@context'] === 'https://schema.org', 'schema.org context');
assert(website['@type'] === 'WebSite', 'WebSite type');
assert(website.url === 'https://gpuorbit.dev/', 'WebSite URL');
assert(website.name === 'GPUOrbit', 'WebSite name');

assert(/^User-agent:\s*\*\s*$/mi.test(robots), 'robots.txt crawler group');
assert(/^Sitemap:\s*https:\/\/gpuorbit\.dev\/sitemap\.xml\s*$/mi.test(robots), 'robots.txt sitemap link');
for (const path of ['/app', '/login', '/signup']) {
  assert(robots.includes(`Disallow: ${path}`), `restricted route ${path}`);
}
assert(sitemap.includes('xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'), 'sitemap XML namespace');
assert((sitemap.match(/<loc>/g) ?? []).length === 1, 'only one public sitemap URL');
assert(sitemap.includes('<loc>https://gpuorbit.dev/</loc>'), 'canonical homepage in sitemap');

console.log('SEO checks passed: metadata, canonical, JSON-LD, robots.txt, sitemap.xml, and CSP.');
