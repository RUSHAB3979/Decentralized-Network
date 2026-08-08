import React from 'react';
import Nav from './components/Nav';
import Hero from './components/Hero';
import HowItWorks from './components/HowItWorks';
import Features from './components/Features';
import Marketplace from './components/Marketplace';
import GameRail from './components/GameRail';
import CTA from './components/CTA';
import Footer from './components/Footer';
import GlowCursor from './components/fx/GlowCursor';
import AuthPage from './components/AuthPage';
/**
 * NodeForge — liquid-GPU landing page.
 * Art direction: obsidian canvas, iridescent fluid ribbon, wireframe globe,
 * Instrument Serif display × Space Grotesk body × JetBrains mono telemetry.
 */
const App = () => {
    const basePath = import.meta.env.BASE_URL.replace(/\/$/, '');
    const pathname = window.location.pathname;
    const relativePath = basePath && pathname.startsWith(basePath)
        ? pathname.slice(basePath.length)
        : pathname;
    const path = relativePath.replace(/\/$/, '') || '/';
    if (path === '/login' || path === '/signup') {
        return <AuthPage initialMode={path === '/signup' ? 'signup' : 'login'}/>;
    }
    return (<div className="relative min-h-screen bg-[#03040c]">
    <GlowCursor />
    <Nav />
    <main>
      <Hero />
      <HowItWorks />
      <Features />
      <Marketplace />
      <GameRail />
      <CTA />
    </main>
    <Footer />
  </div>);
};
export default App;
