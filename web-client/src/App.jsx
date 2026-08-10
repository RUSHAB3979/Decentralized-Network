import React, { useEffect, useState } from 'react';
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
import AppShell from './components/app/AppShell';
import MarketplaceDashboard from './components/app/MarketplaceDashboard';
import RenderJobPage from './components/app/RenderJobPage';
import ModelApiPage from './components/app/ModelApiPage';
import WorkstationPage from './components/app/WorkstationPage';
import GamingPage from './components/app/GamingPage';
import ProviderConsolePage from './components/app/ProviderConsolePage';
import BillingPage from './components/app/BillingPage';
/**
 * NodeForge — liquid-GPU landing page.
 * Art direction: obsidian canvas, iridescent fluid ribbon, wireframe globe,
 * Instrument Serif display × Space Grotesk body × JetBrains mono telemetry.
 */
const App = () => {
    const basePath = import.meta.env.BASE_URL.replace(/\/$/, '');
    const getRoute = () => {
        if (window.location.hash.startsWith('#/')) {
            return window.location.hash.slice(1).replace(/\/$/, '') || '/';
        }
        const pathname = window.location.pathname;
        const relativePath = basePath && pathname.startsWith(basePath)
            ? pathname.slice(basePath.length)
            : pathname;
        return relativePath.replace(/\/$/, '') || '/';
    };
    const [route, setRoute] = useState(getRoute);
    useEffect(() => {
        const syncRoute = () => setRoute(getRoute());
        window.addEventListener('hashchange', syncRoute);
        window.addEventListener('popstate', syncRoute);
        return () => {
            window.removeEventListener('hashchange', syncRoute);
            window.removeEventListener('popstate', syncRoute);
        };
    }, []);
    const navigate = (nextRoute) => {
        window.location.hash = nextRoute;
        setRoute(nextRoute);
        window.scrollTo({ top: 0, behavior: 'auto' });
    };
    if (route === '/login' || route === '/signup') {
        return <AuthPage initialMode={route === '/signup' ? 'signup' : 'login'}/>;
    }
    if (route.startsWith('/app')) {
        let page = <MarketplaceDashboard onNavigate={navigate}/>;
        if (route === '/app/render') page = <RenderJobPage onNavigate={navigate}/>;
        if (route === '/app/models') page = <ModelApiPage onNavigate={navigate}/>;
        if (route === '/app/workstations') page = <WorkstationPage onNavigate={navigate}/>;
        if (route === '/app/gaming') page = <GamingPage onNavigate={navigate}/>;
        if (route === '/app/provider') page = <ProviderConsolePage onNavigate={navigate}/>;
        if (route === '/app/billing') page = <BillingPage onNavigate={navigate}/>;
        return <AppShell currentRoute={route} onNavigate={navigate}>{page}</AppShell>;
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
