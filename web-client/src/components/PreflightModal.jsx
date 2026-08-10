import React, { useState, useEffect, useCallback, useRef } from 'react';
import { X, Loader2, CheckCircle2, Clock, Activity, AlertTriangle, Wifi, Shield, } from 'lucide-react';
import { runPreflightCheck, subscribeSessionStateMachine } from '../services/api';
const SESSION_LIFECYCLE = [
    'requested',
    'eligibility_checked',
    'offered',
    'accepted',
    'reserved',
    'launching',
    'signaling',
    'connecting',
    'live',
];
const STATE_LABELS = {
    requested: 'Requested',
    eligibility_checked: 'Eligibility',
    offered: 'Offered',
    accepted: 'Accepted',
    reserved: 'Reserved',
    launching: 'Launching',
    signaling: 'Signaling',
    connecting: 'Connecting',
    live: 'Live',
};
const PreflightModal = ({ title, onClose, onSessionReady }) => {
    const [preflight, setPreflight] = useState(null);
    const [preflightLoading, setPreflightLoading] = useState(true);
    const [consentChecked, setConsentChecked] = useState(false);
    const [sessionStarted, setSessionStarted] = useState(false);
    const [currentState, setCurrentState] = useState(null);
    const unsubRef = useRef(null);
    useEffect(() => {
        let cancelled = false;
        runPreflightCheck().then((result) => {
            if (!cancelled) {
                setPreflight(result);
                setPreflightLoading(false);
            }
        });
        return () => {
            cancelled = true;
        };
    }, []);
    useEffect(() => {
        return () => {
            unsubRef.current?.();
        };
    }, []);
    const handleLaunch = useCallback(() => {
        if (!consentChecked || !preflight)
            return;
        setSessionStarted(true);
        const unsub = subscribeSessionStateMachine((state) => {
            setCurrentState(state);
            if (state === 'live') {
                onSessionReady('live');
            }
        });
        unsubRef.current = unsub;
    }, [consentChecked, preflight, onSessionReady]);
    const currentStateIndex = currentState
        ? SESSION_LIFECYCLE.indexOf(currentState)
        : -1;
    const canLaunch = consentChecked && preflight !== null && preflight.passed && !sessionStarted;
    return (<div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs">
      <div className="relative w-full max-w-2xl mx-4 rounded-2xl border border-white/10 bg-slate-900/95 shadow-2xl backdrop-blur-xl">
        {/* Header */}
        <div className="flex items-start justify-between border-b border-white/10 px-6 py-5">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-white truncate">
              {title.title}
            </h2>
            <p className="mt-1 text-sm text-slate-400">
              Preflight Diagnostic &amp; Session Initiation
            </p>
          </div>
          <button onClick={onClose} className="ml-4 shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-white" aria-label="Close">
            <X className="h-5 w-5"/>
          </button>
        </div>

        <div className="px-6 py-5 space-y-6">
          {/* Network Preflight Box */}
          <div className="rounded-xl border border-white/10 bg-slate-800/50 p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-slate-300 flex items-center gap-2">
                <Activity className="h-4 w-4 text-indigo-400"/>
                Network Preflight
              </h3>
              {preflight && (<span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${preflight.passed
                ? 'bg-emerald-500/20 text-emerald-400'
                : 'bg-red-500/20 text-red-400'}`}>
                  {preflight.passed ? (<>
                      <CheckCircle2 className="h-3 w-3"/>
                      Preflight Passed
                    </>) : (<>
                      <AlertTriangle className="h-3 w-3"/>
                      Preflight Failed
                    </>)}
                </span>)}
            </div>

            {preflightLoading ? (<div className="flex items-center justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-indigo-400"/>
                <span className="ml-3 text-sm text-slate-400">
                  Running network diagnostics…
                </span>
              </div>) : preflight ? (<div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <MetricTile label="RTT" value={`${Math.round(preflight.rtt_ms)}ms`} icon={<Clock className="h-4 w-4"/>} status={preflight.rtt_ms < 80 ? 'good' : preflight.rtt_ms < 150 ? 'warn' : 'bad'}/>
                <MetricTile label="Jitter" value={`${Number(preflight.jitter_ms).toFixed(1)}ms`} icon={<Activity className="h-4 w-4"/>} status={preflight.jitter_ms < 10 ? 'good' : preflight.jitter_ms < 30 ? 'warn' : 'bad'}/>
                <MetricTile label="Packet Loss" value={`${Number(preflight.packet_loss_pct).toFixed(2)}%`} icon={<AlertTriangle className="h-4 w-4"/>} status={preflight.packet_loss_pct < 1 ? 'good' : preflight.packet_loss_pct < 5 ? 'warn' : 'bad'}/>
                <MetricTile label="Route Mode" value={preflight.connection_type === 'direct_p2p' ? 'Direct P2P' : 'TURN Relay'} icon={<Wifi className="h-4 w-4"/>} status={preflight.connection_type === 'direct_p2p' ? 'good' : 'warn'}/>
              </div>) : null}
          </div>

          {/* Consent Checkbox */}
          <label className="flex items-start gap-3 cursor-pointer group">
            <input type="checkbox" checked={consentChecked} onChange={(e) => setConsentChecked(e.target.checked)} className="mt-0.5 h-4 w-4 rounded-sm border-slate-600 bg-slate-800 text-indigo-500 focus:ring-indigo-500 focus:ring-offset-0 focus:ring-offset-slate-900"/>
            <span className="text-sm text-slate-400 group-hover:text-slate-300 transition-colors leading-relaxed">
              <Shield className="inline h-3.5 w-3.5 mr-1 text-indigo-400 -translate-y-px"/>
              I understand this technical demo runs on dedicated test hardware under controlled
              conditions. Session telemetry may be collected for diagnostics. No personal data
              is transmitted beyond connection negotiation.
            </span>
          </label>

          {/* Session Lifecycle Tracker */}
          {sessionStarted && (<div className="rounded-xl border border-white/10 bg-slate-800/50 p-4">
              <h3 className="text-sm font-medium text-slate-300 mb-4">
                Session Lifecycle
              </h3>

              {/* Progress Bar */}
              <div className="flex items-center gap-1 mb-3">
                {SESSION_LIFECYCLE.map((state, idx) => {
                const isCompleted = currentStateIndex > idx;
                const isCurrent = currentStateIndex === idx;
                return (<div key={state} className={`h-1.5 flex-1 rounded-full transition-all duration-500 ${isCompleted
                        ? 'bg-emerald-500'
                        : isCurrent
                            ? 'bg-indigo-500 animate-pulse'
                            : 'bg-slate-700'}`}/>);
            })}
              </div>

              {/* State Labels */}
              <div className="flex flex-wrap gap-1.5">
                {SESSION_LIFECYCLE.map((state, idx) => {
                const isCompleted = currentStateIndex > idx;
                const isCurrent = currentStateIndex === idx;
                return (<span key={state} className={`inline-flex items-center rounded-sm px-1.5 py-0.5 text-[10px] font-mono font-medium transition-all duration-300 ${isCompleted
                        ? 'bg-emerald-500/20 text-emerald-400'
                        : isCurrent
                            ? 'bg-indigo-500/20 text-indigo-300 animate-pulse'
                            : 'bg-slate-800 text-slate-600'}`}>
                      {STATE_LABELS[state]}
                    </span>);
            })}
              </div>

              {/* Current State Display */}
              {currentState && (<p className="mt-3 text-xs text-slate-400 font-mono">
                  Current state:{' '}
                  <span className="text-indigo-300 font-semibold">
                    {STATE_LABELS[currentState] ?? currentState}
                  </span>
                </p>)}
            </div>)}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-white/10 px-6 py-4">
          <button onClick={onClose} className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 transition-colors hover:bg-white/10 hover:text-white">
            Cancel
          </button>
          <button onClick={handleLaunch} disabled={!canLaunch} className={`rounded-lg px-5 py-2 text-sm font-semibold transition-all ${canLaunch
            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25 hover:bg-indigo-500'
            : 'bg-slate-700 text-slate-500 cursor-not-allowed'}`}>
            Confirm &amp; Connect
          </button>
        </div>
      </div>
    </div>);
};
const MetricTile = ({ label, value, icon, status }) => {
    const colors = {
        good: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5',
        warn: 'text-amber-400 border-amber-500/20 bg-amber-500/5',
        bad: 'text-red-400 border-red-500/20 bg-red-500/5',
    };
    return (<div className={`rounded-lg border p-3 text-center transition-all overflow-hidden ${colors[status]}`}>
      <div className="flex items-center justify-center mb-1.5 opacity-70">
        {icon}
      </div>
      <p className="text-base font-semibold font-mono truncate" title={value}>{value}</p>
      <p className="mt-0.5 text-[10px] uppercase tracking-wider text-slate-500">
        {label}
      </p>
    </div>);
};
export default PreflightModal;
