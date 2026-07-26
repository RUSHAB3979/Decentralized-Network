import React, { useState, useCallback, useRef, useEffect } from 'react';
import { Play, Square, Activity, Gauge, Volume2, VolumeX, Maximize2, Crosshair } from 'lucide-react';
import type { GameTitle, SessionStats } from '../types';

interface SessionPlayerProps {
  title: GameTitle | null;
  stats: SessionStats | null;
  onEndSession: () => void;
  onOpenDebugger: () => void;
}

const SessionPlayer: React.FC<SessionPlayerProps> = ({ title, stats, onEndSession, onOpenDebugger }) => {
  const [showStats, setShowStats] = useState(false);
  const [muted, setMuted] = useState(false);
  const [pointerLocked, setPointerLocked] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handlePointerLockChange = () => {
      setPointerLocked(document.pointerLockElement === containerRef.current);
    };
    document.addEventListener('pointerlockchange', handlePointerLockChange);
    return () => {
      document.removeEventListener('pointerlockchange', handlePointerLockChange);
    };
  }, []);

  const toggleStats = useCallback(() => setShowStats((v) => !v), []);
  const toggleMute = useCallback(() => setMuted((v) => !v), []);
  const togglePointerLock = useCallback(() => {
    if (document.pointerLockElement === containerRef.current) {
      document.exitPointerLock?.();
      setPointerLocked(false);
    } else {
      containerRef.current?.requestPointerLock?.();
      setPointerLocked(true);
    }
  }, []);
  const handleFullscreen = useCallback(() => {
    if (document.fullscreenElement) {
      document.exitFullscreen();
    } else {
      document.documentElement.requestFullscreen();
    }
  }, []);

  return (
    <div className="space-y-4">
      {/* Top Bar */}
      <div className="flex items-center justify-between gap-4 rounded-xl border border-slate-800 bg-slate-900/80 px-5 py-3 backdrop-blur">
        <div className="flex items-center gap-3 min-w-0">
          <span className="relative flex h-3 w-3 shrink-0">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex h-3 w-3 rounded-full bg-emerald-500" />
          </span>
          <span className="text-sm font-medium text-emerald-400">Active WebRTC Stream Session</span>
          {title && (
            <>
              <span className="text-slate-600">—</span>
              <span className="truncate text-sm font-semibold text-slate-200">{title.title}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onOpenDebugger}
            className="flex items-center gap-1.5 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 transition-colors hover:border-indigo-500/50 hover:text-indigo-400"
          >
            <Activity className="h-3.5 w-3.5" />
            Input Debugger
          </button>
          <button
            onClick={onEndSession}
            className="flex items-center gap-1.5 rounded-lg bg-red-600/90 px-3 py-1.5 text-xs font-bold text-white transition-colors hover:bg-red-500"
          >
            <Square className="h-3.5 w-3.5 fill-current" />
            Emergency Stop
          </button>
        </div>
      </div>

      {/* Video Viewport */}
      <div ref={containerRef} className="relative aspect-video overflow-hidden rounded-2xl border border-slate-800 bg-slate-950">
        {/* Blurred background cover */}
        {title?.cover_url && (
          <img
            src={title.cover_url}
            alt=""
            className="absolute inset-0 h-full w-full object-cover blur-2xl brightness-[0.3] saturate-150"
          />
        )}

        {/* Scanline overlay */}
        <div
          className="pointer-events-none absolute inset-0 opacity-[0.03]"
          style={{
            backgroundImage: 'repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,0,0,0.4) 2px, rgba(0,0,0,0.4) 4px)',
          }}
        />

        {/* Centered info card */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="rounded-2xl border border-slate-700/60 bg-slate-900/70 px-8 py-6 text-center backdrop-blur-xl">
            <div className="mb-3 flex items-center justify-center gap-2 text-indigo-400">
              <Play className="h-5 w-5 fill-current" />
              <span className="text-sm font-semibold tracking-wide uppercase">WebRTC Stream</span>
            </div>
            <p className="text-lg font-bold text-slate-100">1080p @ 60 FPS</p>
            <p className="mt-1 text-sm text-slate-400">Interactive Session Ready</p>

            {/* Pointer lock indicator */}
            <div className={`mt-4 flex items-center justify-center gap-1.5 text-xs font-medium transition-colors ${pointerLocked ? 'text-emerald-400' : 'text-slate-500'}`}>
              <Crosshair className="h-3.5 w-3.5" />
              {pointerLocked ? 'Pointer Locked' : 'Pointer Unlocked'}
            </div>
          </div>
        </div>

        {/* Stats overlay (top-left, toggleable) */}
        {showStats && stats && (
          <div className="absolute left-3 top-3 rounded-xl border border-slate-700/50 bg-slate-950/80 p-4 backdrop-blur-lg">
            <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wider text-indigo-400">
              <Gauge className="h-3.5 w-3.5" />
              WebRTC Telemetry
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 font-mono text-xs">
              <div className="text-slate-400">
                FPS <span className="ml-1 text-slate-200">{stats.fps}</span>
              </div>
              <div className="text-slate-400">
                Bitrate{' '}
                <span className="ml-1 text-slate-200">
                  {stats.bitrate_kbps >= 1000
                    ? `${(stats.bitrate_kbps / 1000).toFixed(1)} Mbps`
                    : `${stats.bitrate_kbps} kbps`}
                </span>
              </div>
              <div className="text-slate-400">
                RTT <span className="ml-1 text-slate-200">{stats.rtt_ms} ms</span>
              </div>
              <div className="text-slate-400">
                Loss <span className="ml-1 text-slate-200">{stats.packet_loss_pct}%</span>
              </div>
              <div className="text-slate-400">
                Codec <span className="ml-1 text-slate-200">{stats.codec}</span>
              </div>
              <div className="text-slate-400">
                Drops{' '}
                <span className={`ml-1 ${stats.frames_dropped > 10 ? 'text-amber-400' : 'text-slate-200'}`}>
                  {stats.frames_dropped}/{stats.frames_decoded}
                </span>
              </div>
            </div>
            <div className="mt-2.5 pt-2 border-t border-slate-700/50">
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                  stats.connection_mode === 'direct_p2p'
                    ? 'bg-emerald-500/10 text-emerald-400 ring-1 ring-emerald-500/20'
                    : 'bg-amber-500/10 text-amber-400 ring-1 ring-amber-500/20'
                }`}
              >
                {stats.connection_mode === 'direct_p2p' ? 'Direct P2P' : 'TURN Relay'}
              </span>
            </div>
          </div>
        )}

        {/* Control bar (bottom-right) */}
        <div className="absolute bottom-3 right-3 flex items-center gap-1.5">
          <button
            onClick={toggleStats}
            aria-label="Toggle WebRTC Telemetry Stats"
            title="Toggle stats"
            className={`rounded-lg p-2 backdrop-blur transition-colors ${
              showStats
                ? 'bg-indigo-500/20 text-indigo-400 ring-1 ring-indigo-500/30'
                : 'bg-slate-800/70 text-slate-400 hover:text-slate-200'
            }`}
          >
            <Gauge className="h-4 w-4" />
          </button>
          <button
            onClick={toggleMute}
            aria-label={muted ? 'Unmute Audio' : 'Mute Audio'}
            title={muted ? 'Unmute' : 'Mute'}
            className={`rounded-lg p-2 backdrop-blur transition-colors ${
              muted
                ? 'bg-red-500/20 text-red-400 ring-1 ring-red-500/30'
                : 'bg-slate-800/70 text-slate-400 hover:text-slate-200'
            }`}
          >
            {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
          </button>
          <button
            onClick={togglePointerLock}
            aria-label={pointerLocked ? 'Release Pointer Lock' : 'Engage Pointer Lock'}
            title={pointerLocked ? 'Release pointer' : 'Lock pointer'}
            className={`rounded-lg p-2 backdrop-blur transition-colors ${
              pointerLocked
                ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30'
                : 'bg-slate-800/70 text-slate-400 hover:text-slate-200'
            }`}
          >
            <Crosshair className="h-4 w-4" />
          </button>
          <button
            onClick={handleFullscreen}
            aria-label="Toggle Fullscreen"
            title="Fullscreen"
            className="rounded-lg bg-slate-800/70 p-2 text-slate-400 backdrop-blur transition-colors hover:text-slate-200"
          >
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default SessionPlayer;
