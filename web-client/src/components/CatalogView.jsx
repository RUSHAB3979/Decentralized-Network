import React from 'react';
import { ShieldCheck, Cpu, Zap, Play, Layers, AlertTriangle } from 'lucide-react';
const rightsBadgeStyles = {
    written_permission: {
        bg: 'bg-emerald-500/10',
        text: 'text-emerald-400',
        border: 'border-emerald-500/30',
        label: 'Written Permission',
    },
    platform_program: {
        bg: 'bg-blue-500/10',
        text: 'text-blue-400',
        border: 'border-blue-500/30',
        label: 'Platform Program',
    },
    internal_demo_only: {
        bg: 'bg-purple-500/10',
        text: 'text-purple-400',
        border: 'border-purple-500/30',
        label: 'Internal Demo Only',
    },
    counsel_approved: {
        bg: 'bg-sky-500/10',
        text: 'text-sky-400',
        border: 'border-sky-500/30',
        label: 'Counsel Approved',
    },
    blocked: {
        bg: 'bg-amber-500/10',
        text: 'text-amber-400',
        border: 'border-amber-500/30',
        label: 'Blocked',
    },
};
const CatalogView = ({ titles, onSelectTitle }) => {
    return (<div className="space-y-8">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-indigo-600/20 via-purple-600/15 to-slate-900 border border-indigo-500/20 p-8 md:p-12">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-indigo-500/10 via-transparent to-transparent"/>
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 rounded-full bg-indigo-500/15 border border-indigo-400/30 px-4 py-1.5 text-sm font-medium text-indigo-300 mb-4">
            <Zap className="h-4 w-4"/>
            Milestone M0 &amp; Phase G Client Baseline
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-white mb-3">
            Authorized Cloud Gaming Catalog
          </h1>
          <p className="text-slate-400 max-w-2xl text-lg leading-relaxed">
            Browse publisher-approved titles available for P2P cloud streaming.
            Each listing reflects real-time host availability, hardware
            requirements, and commercial rights status.
          </p>
        </div>
      </div>

      {/* Title Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {titles.map((title) => {
            const rights = rightsBadgeStyles[title.approval.rights_basis];
            const isBlocked = title.approval.rights_basis === 'blocked';
            return (<div key={title.id} className="group flex flex-col rounded-xl bg-slate-900/60 backdrop-blur-sm border border-slate-700/50 overflow-hidden hover:border-indigo-500/40 transition-colors duration-300">
              {/* Cover Image */}
              <div className="relative aspect-video overflow-hidden">
                <img src={title.cover_url} alt={title.title} className="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"/>
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-transparent"/>

                {/* Active Hosts Badge (top-right) */}
                <div className="absolute top-3 right-3 inline-flex items-center gap-1.5 rounded-full bg-slate-900/80 backdrop-blur-sm border border-slate-700/60 px-3 py-1 text-xs font-medium text-slate-200">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"/>
                  {title.active_hosts_count} Hosts Ready
                </div>

                {/* Genre Tag + Title (bottom) */}
                <div className="absolute bottom-3 left-3 right-3">
                  <span className="inline-flex items-center gap-1 rounded-md bg-slate-800/80 backdrop-blur-sm px-2 py-0.5 text-xs font-medium text-slate-300 mb-2">
                    <Layers className="h-3 w-3"/>
                    {title.genre}
                  </span>
                  <h3 className="text-lg font-semibold text-white truncate">
                    {title.title}
                  </h3>
                </div>
              </div>

              {/* Body */}
              <div className="flex flex-1 flex-col p-4 space-y-4">
                {/* Description */}
                <p className="text-sm text-slate-400 line-clamp-2 leading-relaxed">
                  {title.description}
                </p>

                {/* Rights Approval Badge */}
                <div className={`inline-flex items-center gap-1.5 self-start rounded-full border px-3 py-1 text-xs font-medium ${rights.bg} ${rights.text} ${rights.border}`}>
                  {isBlocked ? (<AlertTriangle className="h-3.5 w-3.5"/>) : (<ShieldCheck className="h-3.5 w-3.5"/>)}
                  {rights.label}
                </div>

                {/* Hardware Specs Panel */}
                <div className="rounded-lg bg-slate-800/50 border border-slate-700/40 p-3 space-y-2 text-xs">
                  <div className="flex items-center gap-2 text-slate-400">
                    <Cpu className="h-3.5 w-3.5 text-slate-500 shrink-0"/>
                    <span className="text-slate-500">GPU</span>
                    <span className="ml-auto font-mono text-slate-300">
                      {title.requirements.gpu}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-400">
                    <Zap className="h-3.5 w-3.5 text-slate-500 shrink-0"/>
                    <span className="text-slate-500">Encoder</span>
                    <span className="ml-auto font-mono text-slate-300">
                      {title.requirements.encoder_required}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-400">
                    <Layers className="h-3.5 w-3.5 text-slate-500 shrink-0"/>
                    <span className="text-slate-500">Min Downlink</span>
                    <span className="ml-auto font-mono text-slate-300">
                      {title.requirements.recommended_downlink_mbps} Mbps
                    </span>
                  </div>
                </div>
              </div>

              {/* Footer */}
              <div className="p-4 pt-0">
                <button type="button" onClick={() => onSelectTitle(title)} disabled={isBlocked} className={`w-full inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2 focus:ring-offset-slate-900 ${isBlocked
                    ? 'bg-slate-800 text-amber-400 opacity-80 cursor-not-allowed border border-amber-500/30'
                    : 'bg-indigo-600 text-white hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-indigo-600'}`}>
                  {isBlocked ? (<>
                      <AlertTriangle className="h-4 w-4 text-amber-400"/>
                      <span>Commercial Rights Blocked</span>
                    </>) : (<>
                      <Play className="h-4 w-4"/>
                      <span>Request Streaming Session</span>
                    </>)}
                </button>
              </div>
            </div>);
        })}
      </div>
    </div>);
};
export default CatalogView;
