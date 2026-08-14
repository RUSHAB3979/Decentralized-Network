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
import { useSession } from './hooks/useSession';
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
    // Called unconditionally, before any early return: React requires hooks to
    // run in the same order on every render, and the /login branch below returns
    // early.
    const session = useSession();
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
        // The dashboard reads the signed-in account's keys, so rendering it for
        // an anonymous visitor means every panel 401s. Three states, not two:
        // 'loading' must not render the app *or* bounce to login, because the
        // stored token has not been checked yet and doing either produces a
        // visible flash of the wrong page on every reload.
        if (session.status === 'loading') {
            return (<div className="grid min-h-[100svh] place-items-center bg-[#03040c] text-slate-500">
        <p className="font-mono text-[11px] uppercase tracking-[0.24em]">Restoring session…</p>
      </div>);
        }
        if (session.status === 'anonymous') {
            return <AuthPage initialMode="login"/>;
        }
        if (session.status === 'error') {
            // The session may be perfectly valid; we could not check it. Saying
            // "signed out" here would be a guess, and the wrong one -- it would
            // send someone to re-enter a password that is not the problem.
            return (<div className="grid min-h-[100svh] place-items-center bg-[#03040c] px-6 text-center">
        <div className="max-w-md">
          <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-amber-300">Orchestrator unreachable</p>
          <p className="mt-4 text-sm leading-6 text-slate-400">{session.error}</p>
          <p className="mt-2 text-sm leading-6 text-slate-500">Your session has not been ended — this is a connection problem. Start the orchestrator and try again.</p>
          <button type="button" onClick={session.refresh} className="btn-liquid mt-7 !inline-flex !py-3">Retry</button>
        </div>
      </div>);
        }

        let page = <MarketplaceDashboard onNavigate={navigate}/>;
        if (route === '/app/render') page = <RenderJobPage onNavigate={navigate}/>;
        if (route === '/app/models') page = <ModelApiPage onNavigate={navigate}/>;
        if (route === '/app/workstations') page = <WorkstationPage onNavigate={navigate}/>;
        if (route === '/app/gaming') page = <GamingPage onNavigate={navigate}/>;
        if (route === '/app/provider') page = <ProviderConsolePage onNavigate={navigate}/>;
        if (route === '/app/billing') page = <BillingPage onNavigate={navigate}/>;
        return <AppShell currentRoute={route} onNavigate={navigate} session={session}>{page}</AppShell>;
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
