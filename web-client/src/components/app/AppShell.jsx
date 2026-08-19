import React, { useEffect, useRef, useState } from 'react';
import {
  Activity,
  Bell,
  BrainCircuit,
  Clapperboard,
  Gamepad2,
  LayoutDashboard,
  Menu,
  MonitorUp,
  Search,
  Server,
  WalletCards,
  X,
} from 'lucide-react';
import Logo from '../Logo';

const NAV_ITEMS = [
  { label: 'Overview', route: '/app', icon: LayoutDashboard },
  { label: 'Render & media', route: '/app/render', icon: Clapperboard },
  { label: 'Model APIs', route: '/app/models', icon: BrainCircuit },
  { label: 'Workstations', route: '/app/workstations', icon: MonitorUp },
  { label: 'Cloud gaming', route: '/app/gaming', icon: Gamepad2 },
];

const ACCOUNT_ITEMS = [
  { label: 'Provider console', route: '/app/provider', icon: Server },
  { label: 'Usage & billing', route: '/app/billing', icon: WalletCards },
];

const routeIsActive = (currentRoute, route) => {
  if (route === '/app') return currentRoute === '/app';
  return currentRoute.startsWith(route);
};

const AppShell = ({ currentRoute, onNavigate, children, session }) => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [signingOut, setSigningOut] = useState(false);

  const account = session?.user ?? null;
  // Initials from the display name if there is one, otherwise the email. Falls
  // back to a dash rather than empty so the avatar never collapses to a blank
  // circle that looks like a loading state that never finished.
  const initials = (() => {
    const source = account?.display_name || account?.email || '';
    const letters = source.trim().split(/[\s@._-]+/).filter(Boolean).slice(0, 2);
    return letters.length ? letters.map((part) => part[0].toUpperCase()).join('') : '—';
  })();

  const signOut = async () => {
    setSigningOut(true);
    try {
      await session?.logout?.();
      // Land on the public page, not on /login. Being bounced straight to a
      // login form after choosing to sign out reads as the sign-out having
      // failed.
      navigate('/');
    }
    finally {
      setSigningOut(false);
    }
  };
  const searchRef = useRef(null);
  const searchableItems = [...NAV_ITEMS, ...ACCOUNT_ITEMS];
  const searchResults = searchableItems.filter((item) => item.label.toLowerCase().includes(query.toLowerCase()));

  useEffect(() => {
    const focusSearch = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        searchRef.current?.focus();
        setSearchOpen(true);
      }
      if (event.key === 'Escape') {
        setSearchOpen(false);
        setNotificationsOpen(false);
        setProfileOpen(false);
      }
    };
    window.addEventListener('keydown', focusSearch);
    return () => window.removeEventListener('keydown', focusSearch);
  }, []);

  const navigate = (route) => {
    setMobileOpen(false);
    setSearchOpen(false);
    setQuery('');
    setNotificationsOpen(false);
    setProfileOpen(false);
    onNavigate(route);
  };

  const NavButton = ({ item }) => {
    const active = routeIsActive(currentRoute, item.route);
    return (
      <button
        type="button"
        onClick={() => navigate(item.route)}
        className={`group flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-[13px] transition-all ${
          active
            ? 'bg-white/[0.07] text-white shadow-[inset_0_0_0_1px_rgba(255,255,255,.06)]'
            : 'text-slate-500 hover:bg-white/[0.035] hover:text-slate-200'
        }`}
      >
        <item.icon className={`h-[17px] w-[17px] ${active ? 'text-cyan-300' : 'text-slate-600 group-hover:text-slate-300'}`} />
        <span className="font-medium">{item.label}</span>
        {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-cyan-300 shadow-[0_0_12px_rgba(103,232,249,.8)]" />}
      </button>
    );
  };

  const sidebar = (
    <div className="flex h-full flex-col">
      <button type="button" onClick={() => navigate('/')} className="flex h-[72px] items-center gap-3 border-b border-white/[0.06] px-5 text-left">
        <Logo className="h-8 w-8" />
        <span className="flex flex-col leading-none">
          <span className="text-[15px] font-semibold tracking-tight text-slate-100">NodeForge</span>
          <span className="mt-1 font-mono text-[8px] uppercase tracking-[0.28em] text-slate-600">Compute console</span>
        </span>
      </button>

      <div className="px-3 py-5">
        <p className="px-3 font-mono text-[9px] uppercase tracking-[0.24em] text-slate-700">Marketplace</p>
        <div className="mt-2 space-y-1">
          {NAV_ITEMS.map((item) => <NavButton key={item.route} item={item} />)}
        </div>
      </div>

      <div className="px-3 pb-5">
        <p className="px-3 font-mono text-[9px] uppercase tracking-[0.24em] text-slate-700">Account</p>
        <div className="mt-2 space-y-1">
          {ACCOUNT_ITEMS.map((item) => <NavButton key={item.route} item={item} />)}
        </div>
      </div>

      <div className="mt-auto border-t border-white/[0.06] p-4">
        <div className="rounded-xl border border-white/[0.07] bg-white/[0.025] p-3.5">
          <div className="flex items-center gap-2 text-[11px] font-medium text-slate-300">
            <Activity className="h-3.5 w-3.5 text-emerald-400" />
            Partly live console
          </div>
          <p className="mt-2 text-[11px] leading-5 text-slate-600">Model APIs and Blender renders use live orchestrator endpoints. Billing, workstations, gaming, and render pricing remain preview data.</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-[#07080d] text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-[244px] border-r border-white/[0.06] bg-[#0a0b11] md:block">
        {sidebar}
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <button type="button" aria-label="Close navigation" className="absolute inset-0 bg-black/75 backdrop-blur-xs" onClick={() => setMobileOpen(false)} />
          <aside className="relative h-full w-[280px] border-r border-white/[0.08] bg-[#0a0b11] shadow-2xl">
            <button type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)} className="absolute right-3 top-5 rounded-lg p-2 text-slate-500 hover:bg-white/[0.05] hover:text-white">
              <X className="h-4 w-4" />
            </button>
            {sidebar}
          </aside>
        </div>
      )}

      <div className="md:pl-[244px]">
        <header className="sticky top-0 z-30 flex h-[72px] items-center gap-4 border-b border-white/[0.06] bg-[#07080d]/85 px-4 backdrop-blur-xl sm:px-7">
          <button type="button" aria-label="Open navigation" onClick={() => setMobileOpen(true)} className="rounded-lg border border-white/[0.08] p-2 text-slate-400 md:hidden">
            <Menu className="h-4 w-4" />
          </button>
          <div className="relative hidden max-w-md flex-1 sm:block">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-600" />
            <input ref={searchRef} value={query} onChange={(event) => { setQuery(event.target.value); setSearchOpen(true); }} onFocus={() => setSearchOpen(true)} onBlur={() => window.setTimeout(() => setSearchOpen(false), 100)} onKeyDown={(event) => { if (event.key === 'Enter' && searchResults[0]) navigate(searchResults[0].route); }} aria-label="Search marketplace" placeholder="Search products and console pages…" className="h-9 w-full rounded-lg border border-white/[0.07] bg-white/[0.025] pl-9 pr-16 text-xs text-slate-200 outline-hidden placeholder:text-slate-700 focus:border-indigo-400/35" />
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-sm border border-white/[0.07] bg-black/20 px-1.5 py-0.5 font-mono text-[8px] text-slate-600">Ctrl K</kbd>
            {searchOpen && (
              <div className="absolute left-0 right-0 top-11 z-50 rounded-xl border border-white/[0.09] bg-[#0d0f17] p-2 shadow-2xl shadow-black/60">
                <p className="px-2 py-2 font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Console destinations</p>
                {searchResults.length ? searchResults.map((item) => <button key={item.route} type="button" onMouseDown={(event) => event.preventDefault()} onClick={() => navigate(item.route)} className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-xs text-slate-400 hover:bg-white/[0.05] hover:text-white"><item.icon className="h-3.5 w-3.5 text-slate-600" />{item.label}<span className="ml-auto font-mono text-[8px] text-slate-700">Open</span></button>) : <p className="px-3 py-5 text-center text-[11px] text-slate-600">No matching console page</p>}
              </div>
            )}
          </div>
          <div className="ml-auto flex items-center gap-2.5">
            <span className="hidden items-center gap-2 rounded-full border border-emerald-400/15 bg-emerald-400/[0.04] px-3 py-1.5 font-mono text-[9px] uppercase tracking-[0.18em] text-emerald-300 sm:inline-flex">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" /> Local preview
            </span>
            <button type="button" aria-label="Notifications" aria-expanded={notificationsOpen} onClick={() => { setNotificationsOpen((value) => !value); setProfileOpen(false); }} className="rounded-lg border border-white/[0.07] bg-white/[0.025] p-2.5 text-slate-500 transition-colors hover:text-white">
              <Bell className="h-4 w-4" />
            </button>
            <button type="button" aria-label="Open account menu" aria-expanded={profileOpen} onClick={() => { setProfileOpen((value) => !value); setNotificationsOpen(false); }} className="flex h-9 w-9 items-center justify-center rounded-lg bg-linear-to-br from-indigo-300 to-cyan-300 text-xs font-semibold text-[#07080d]">{initials}</button>
            {notificationsOpen && <div className="absolute right-16 top-[60px] w-72 rounded-xl border border-white/[0.09] bg-[#0d0f17] p-4 shadow-2xl shadow-black/60"><p className="text-xs font-medium text-slate-300">Notifications</p><div className="mt-4 flex min-h-28 flex-col items-center justify-center rounded-lg border border-white/[0.06] bg-black/20 p-4 text-center"><Bell className="h-5 w-5 text-slate-800" /><p className="mt-3 text-[11px] text-slate-500">No sandbox notifications</p><p className="mt-1 text-[9px] text-slate-700">Backend events are not connected.</p></div></div>}
            {profileOpen && <div className="absolute right-4 top-[60px] w-64 rounded-xl border border-white/[0.09] bg-[#0d0f17] p-3 shadow-2xl shadow-black/60">
              <div className="border-b border-white/[0.06] px-2 pb-3">
                <p className="truncate text-xs font-medium text-slate-300">{account?.display_name || account?.email || 'Signed in'}</p>
                {account?.display_name && <p className="mt-1 truncate text-[10px] text-slate-600">{account.email}</p>}
              </div>
              <button type="button" onClick={() => navigate('/')} className="mt-2 w-full rounded-lg px-3 py-2.5 text-left text-xs text-slate-500 hover:bg-white/[0.05] hover:text-white">Return to landing page</button>
              <button type="button" onClick={signOut} disabled={signingOut} className="w-full rounded-lg px-3 py-2.5 text-left text-xs text-rose-300/80 hover:bg-rose-500/[0.08] hover:text-rose-200 disabled:opacity-50">{signingOut ? 'Signing out…' : 'Sign out'}</button>
            </div>}
          </div>
        </header>
        <main className="min-h-[calc(100vh-72px)]">{children}</main>
      </div>
    </div>
  );
};

export default AppShell;
