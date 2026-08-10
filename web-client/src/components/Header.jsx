import React from 'react';
import { Gamepad2, Play, Server, Sliders, Shield, Database, Wifi } from 'lucide-react';
const TAB_CONFIG = [
    { key: 'catalog', label: 'Catalog', icon: Gamepad2 },
    { key: 'session', label: 'Session', icon: Play },
    { key: 'telemetry', label: 'Telemetry', icon: Server },
    { key: 'debugger', label: 'Debugger', icon: Sliders },
];
const Header = ({ activeTab, setActiveTab, health, activeSessionState }) => {
    const isSessionLive = activeSessionState === 'live';
    const dbConnected = health?.db === 'ok';
    return (<>
      {/* Sticky top header */}
      <header className="sticky top-0 z-50 bg-slate-950/80 backdrop-blur-xl border-b border-slate-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">

            {/* Brand — left */}
            <div className="flex items-center gap-3 min-w-0">
              <div className="shrink-0 w-10 h-10 rounded-xl bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                <Gamepad2 className="w-5 h-5 text-white"/>
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h1 className="text-white font-semibold text-lg tracking-tight truncate">
                    P2P Cloud Gaming
                  </h1>
                  <span className="hidden sm:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 uppercase tracking-wider">
                    Marketplace
                  </span>
                </div>
                <p className="text-slate-500 text-xs font-mono truncate hidden sm:block">
                  Control-Plane &amp; Session Orchestration
                </p>
              </div>
            </div>

            {/* Navigation tabs — center, hidden on mobile */}
            <nav className="hidden md:flex items-center gap-1">
              {TAB_CONFIG.map(({ key, label, icon: Icon }) => {
            const isActive = activeTab === key;
            return (<button key={key} onClick={() => setActiveTab(key)} className={`relative flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${isActive
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-white hover:bg-slate-800/60'}`}>
                    <Icon className="w-4 h-4"/>
                    <span>{label}</span>
                    {/* Green ping dot for live session on Session tab */}
                    {key === 'session' && isSessionLive && (<span className="absolute top-1 right-1 flex h-2.5 w-2.5">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"/>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"/>
                      </span>)}
                  </button>);
        })}
            </nav>

            {/* Status — right */}
            <div className="flex items-center gap-3">
              {/* Health / DB indicator */}
              <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
                {dbConnected ? (<>
                    <Database className="w-3.5 h-3.5 text-emerald-400"/>
                    <span className="text-xs text-emerald-400 font-medium">
                      Postgres DB: Connected
                    </span>
                  </>) : (<>
                    <Wifi className="w-3.5 h-3.5 text-amber-400"/>
                    <span className="text-xs text-amber-400 font-medium">
                      Orchestrator: Standalone
                    </span>
                  </>)}
              </div>

              {/* Shield / M0 Gate badge */}
              <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
                <Shield className="w-3.5 h-3.5 text-indigo-400"/>
                <span className="text-xs text-indigo-300 font-medium">M0 Gate: OK</span>
              </div>
            </div>

          </div>
        </div>
      </header>

      {/* Mobile tab bar — bottom, visible only below md */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-slate-950/90 backdrop-blur-xl border-t border-slate-800">
        <div className="flex items-center justify-around h-14">
          {TAB_CONFIG.map(({ key, label, icon: Icon }) => {
            const isActive = activeTab === key;
            return (<button key={key} aria-label={label} title={label} onClick={() => setActiveTab(key)} className={`relative flex items-center justify-center w-12 h-12 rounded-xl transition-all duration-200 ${isActive
                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30'
                    : 'text-slate-500 hover:text-white hover:bg-slate-800/60'}`}>
                <Icon className="w-5 h-5"/>
                {key === 'session' && isSessionLive && (<span className="absolute top-1 right-1 flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"/>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"/>
                  </span>)}
              </button>);
        })}
        </div>
      </nav>
    </>);
};
export default Header;
