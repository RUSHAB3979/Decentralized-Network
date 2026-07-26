import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Sliders,
  Trash2,
  Terminal,
  ShieldAlert,
  Keyboard,
  MousePointer,
  Gamepad,
} from 'lucide-react';

interface InputEventLog {
  id: string;
  timestamp: string;
  type: 'keydown' | 'keyup' | 'mousemove' | 'mousedown' | 'mouseup' | 'gamepad';
  details: string;
}

const MAX_LOG_ENTRIES = 50;

const typeIcon: Record<InputEventLog['type'], React.ReactNode> = {
  keydown: <Keyboard className="w-4 h-4 text-indigo-400" />,
  keyup: <Keyboard className="w-4 h-4 text-indigo-300" />,
  mousemove: <MousePointer className="w-4 h-4 text-purple-400" />,
  mousedown: <MousePointer className="w-4 h-4 text-purple-500" />,
  mouseup: <MousePointer className="w-4 h-4 text-purple-300" />,
  gamepad: <Gamepad className="w-4 h-4 text-emerald-400" />,
};

const typeBadgeColor: Record<InputEventLog['type'], string> = {
  keydown: 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30',
  keyup: 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20',
  mousemove: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  mousedown: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  mouseup: 'bg-purple-500/10 text-purple-300 border-purple-500/20',
  gamepad: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30',
};

const InputDebugger: React.FC = () => {
  const [logs, setLogs] = useState<InputEventLog[]>([]);
  const [isListening, setIsListening] = useState(true);
  const idCounter = useRef(0);

  const makeId = useCallback((): string => {
    idCounter.current += 1;
    return `evt-${Date.now()}-${idCounter.current}`;
  }, []);

  const formatTimestamp = useCallback((): string => {
    const d = new Date();
    return d.toLocaleTimeString('en-US', { hour12: false }) + '.' + String(d.getMilliseconds()).padStart(3, '0');
  }, []);

  const pushEntry = useCallback((entry: InputEventLog) => {
    setLogs((prev) => [entry, ...prev].slice(0, MAX_LOG_ENTRIES));
  }, []);

  useEffect(() => {
    if (!isListening) return;

    const onKeyDown = (e: KeyboardEvent) => {
      pushEntry({
        id: makeId(),
        timestamp: formatTimestamp(),
        type: 'keydown',
        details: `Key: ${e.key}  Code: ${e.code}  Shift: ${e.shiftKey}  Ctrl: ${e.ctrlKey}  Alt: ${e.altKey}`,
      });
    };

    const onMouseDown = (e: MouseEvent) => {
      pushEntry({
        id: makeId(),
        timestamp: formatTimestamp(),
        type: 'mousedown',
        details: `Button: ${e.button}  X: ${e.clientX}  Y: ${e.clientY}`,
      });
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('mousedown', onMouseDown);

    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('mousedown', onMouseDown);
    };
  }, [isListening, pushEntry, makeId, formatTimestamp]);

  const handleSimulateGamepad = useCallback(() => {
    const axes = [
      (Math.random() * 2 - 1).toFixed(2),
      (Math.random() * 2 - 1).toFixed(2),
    ];
    const button = Math.floor(Math.random() * 16);
    pushEntry({
      id: makeId(),
      timestamp: formatTimestamp(),
      type: 'gamepad',
      details: `Gamepad 0  Button: ${button} pressed  Axes: [${axes.join(', ')}]`,
    });
  }, [pushEntry, makeId, formatTimestamp]);

  const handleClear = useCallback(() => {
    setLogs([]);
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/20 rounded-lg">
            <Terminal className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">Input Capture &amp; Bounded Debugger</h2>
            <p className="text-sm text-slate-400">
              {isListening ? 'Listening for input events...' : 'Paused'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsListening((v) => !v)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              isListening
                ? 'bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30'
                : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
            }`}
          >
            <Sliders className="w-4 h-4" />
            {isListening ? 'Listening' : 'Paused'}
          </button>
          <button
            onClick={handleSimulateGamepad}
            className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/20 text-purple-300 rounded-lg text-sm font-medium hover:bg-purple-500/30 transition-colors"
          >
            <Gamepad className="w-4 h-4" />
            Simulate Gamepad
          </button>
          <button
            onClick={handleClear}
            className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 text-slate-300 rounded-lg text-sm font-medium hover:bg-slate-600 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            Clear
          </button>
        </div>
      </div>

      {/* Main area: 2 columns on lg */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Left: Live event log (2/3) */}
        <div className="lg:col-span-2 bg-slate-900/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
              Live Event Log
            </h3>
            <span className="text-xs text-slate-500 font-mono">
              {logs.length} / {MAX_LOG_ENTRIES}
            </span>
          </div>

          {logs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-slate-500">
              <Keyboard className="w-12 h-12 mb-3 text-slate-600" />
              <p className="text-sm font-medium">Press any key...</p>
              <p className="text-xs text-slate-600 mt-1">
                Keyboard and mouse events will appear here
              </p>
            </div>
          ) : (
            <div className="space-y-1 max-h-[28rem] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-slate-700">
              {logs.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center gap-3 px-3 py-2 bg-slate-800/50 rounded-lg hover:bg-slate-800/80 transition-colors group"
                >
                  <span className="flex-shrink-0">{typeIcon[entry.type]}</span>
                  <span className="text-xs font-mono text-slate-500 flex-shrink-0 w-24">
                    {entry.timestamp}
                  </span>
                  <span
                    className={`text-xs font-mono px-2 py-0.5 rounded border flex-shrink-0 ${typeBadgeColor[entry.type]}`}
                  >
                    {entry.type}
                  </span>
                  <span className="text-sm font-mono text-slate-300 truncate">
                    {entry.details}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right: Safety principles (1/3) */}
        <div className="space-y-4">
          {/* Bounded Input Injection */}
          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-indigo-500/15 rounded-lg">
                <ShieldAlert className="w-5 h-5 text-indigo-400" />
              </div>
              <h3 className="text-sm font-semibold text-white">Bounded Input Injection</h3>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">
              All captured input is mapped strictly inside the remote session viewport.
              Mouse coordinates are clamped to the stream resolution; keyboard events
              are forwarded only while the player element is focused. No input can
              escape the bounded region or interact with the host OS.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-xs text-emerald-400 font-medium">Enforced</span>
            </div>
          </div>

          {/* Non-Administrator Isolation */}
          <div className="bg-slate-900/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-4">
            <div className="flex items-center gap-3 mb-3">
              <div className="p-2 bg-purple-500/15 rounded-lg">
                <ShieldAlert className="w-5 h-5 text-purple-400" />
              </div>
              <h3 className="text-sm font-semibold text-white">Non-Administrator Isolation</h3>
            </div>
            <p className="text-sm text-slate-400 leading-relaxed">
              Remote sessions run under a restricted, non-administrator Windows account.
              Game processes cannot escalate privileges, modify system settings, or access
              resources outside the sandboxed session directory. Driver-level input injection
              is blocked by policy.
            </p>
            <div className="mt-3 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-xs text-emerald-400 font-medium">Enforced</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default InputDebugger;
