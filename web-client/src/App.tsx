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

/**
 * NodeForge — liquid-GPU landing page.
 * Art direction: obsidian canvas, iridescent fluid ribbon, wireframe globe,
 * Instrument Serif display × Space Grotesk body × JetBrains mono telemetry.
 */
const App: React.FC = () => (
  <div className="relative min-h-screen bg-[#03040c]">
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
  </div>
);

export default App;
