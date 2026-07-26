import React, { useState, useEffect } from 'react';
import { Server, RefreshCw, Globe } from 'lucide-react';
import type { ProviderNode, NodeState } from '../types';
import { MOCK_NODES } from '../services/api';

const clamp = (value: number, min: number, max: number): number =>
  Math.max(min, Math.min(max, value));

const fluctuate = (base: number, range: number, min: number, max: number): number =>
  clamp(base + (Math.random() * 2 - 1) * range, min, max);

interface StateBadgeProps {
  state: NodeState;
}

const StateBadge: React.FC<StateBadgeProps> = ({ state }) => {
  const isActive = state === 'online_idle';
  const isBusy = state === 'reserved' || state === 'streaming';

  const bg = isActive
    ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
    : isBusy
      ? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30'
      : 'bg-slate-500/20 text-slate-400 border-slate-500/30';

  const label = state.replace(/_/g, ' ');

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${bg}`}>
      {(isActive || isBusy) && (
        <span className="relative flex h-2 w-2">
          <span
            className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${
              isActive ? 'bg-emerald-400 animate-ping' : 'bg-indigo-400 animate-ping'
            }`}
          />
          <span
            className={`relative inline-flex rounded-full h-2 w-2 ${
              isActive ? 'bg-emerald-400' : 'bg-indigo-400'
            }`}
          />
        </span>
      )}
      {label}
    </span>
  );
};

interface GpuUtilBarProps {
  pct: number;
}

const GpuUtilBar: React.FC<GpuUtilBarProps> = ({ pct }) => {
  const color =
    pct >= 90
      ? 'bg-red-500'
      : pct >= 70
        ? 'bg-amber-500'
        : pct >= 40
          ? 'bg-indigo-500'
          : 'bg-emerald-500';

  return (
    <div className="flex items-center gap-2 min-w-[120px]">
      <div className="flex-1 h-2 rounded-full bg-slate-700/60 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-slate-300 w-10 text-right">
        {pct.toFixed(0)}%
      </span>
    </div>
  );
};

const NodeTelemetry: React.FC = () => {
  const [nodes, setNodes] = useState<ProviderNode[]>(() =>
    MOCK_NODES.map((n) => ({ ...n, telemetry: { ...n.telemetry } }))
  );

  useEffect(() => {
    const id = setInterval(() => {
      if (document.hidden) return;
      setNodes((prev) =>
        prev.map((node) => ({
          ...node,
          telemetry: {
            ...node.telemetry,
            gpu_utilization_pct: Math.round(
              fluctuate(node.telemetry.gpu_utilization_pct, 3, 0, 100)
            ),
            temp_celsius: Math.round(
              fluctuate(node.telemetry.temp_celsius, 1, 30, 95)
            ),
            power_draw_watts: Math.round(
              fluctuate(node.telemetry.power_draw_watts, 5, 50, 350)
            ),
          },
        }))
      );
    }, 2000);

    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20">
            <Server className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              GPU Provider Nodes &amp; Telemetry
            </h2>
            <p className="text-xs text-slate-400">
              Live hardware metrics from enrolled provider fleet
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50">
          <RefreshCw className="w-3.5 h-3.5 text-emerald-400 animate-spin" style={{ animationDuration: '2s' }} />
          <span className="text-xs font-mono text-slate-400">2s</span>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-xl border border-slate-700/50 bg-slate-900/50 backdrop-blur-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead>
              <tr className="border-b border-slate-700/50">
                <th className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Node ID &amp; Class
                </th>
                <th className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  State
                </th>
                <th className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Hardware Baseline
                </th>
                <th className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  GPU Util
                </th>
                <th className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Thermals
                </th>
                <th className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Power
                </th>
                <th className="px-4 py-3 text-xs font-medium text-slate-400 uppercase tracking-wider">
                  Region &amp; Ping
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/30">
              {nodes.map((node) => {
                const tempHot = node.telemetry.temp_celsius > 75;
                const classLabel = node.host_class.replace(/_/g, ' ');

                return (
                  <tr
                    key={node.node_id}
                    className="hover:bg-slate-800/40 transition-colors"
                  >
                    {/* Node ID & Class */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="font-mono text-xs text-white">
                          {node.node_id}
                        </span>
                        <span className="text-xs text-slate-500 capitalize">
                          {classLabel}
                        </span>
                      </div>
                    </td>

                    {/* State */}
                    <td className="px-4 py-3">
                      <StateBadge state={node.state} />
                    </td>

                    {/* Hardware Baseline */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col">
                        <span className="text-xs text-white">
                          {node.telemetry.gpu_name}
                        </span>
                        <span className="text-xs text-slate-500">
                          {node.telemetry.vram_total_gb} GB VRAM &middot; Driver{' '}
                          {node.telemetry.driver_version}
                        </span>
                      </div>
                    </td>

                    {/* GPU Util */}
                    <td className="px-4 py-3">
                      <GpuUtilBar pct={node.telemetry.gpu_utilization_pct} />
                    </td>

                    {/* Thermals */}
                    <td className="px-4 py-3">
                      <span
                        className={`font-mono text-sm font-medium ${
                          tempHot ? 'text-red-400' : 'text-emerald-400'
                        }`}
                      >
                        {node.telemetry.temp_celsius}°C
                      </span>
                    </td>

                    {/* Power */}
                    <td className="px-4 py-3">
                      <span className="font-mono text-sm text-slate-300">
                        {node.telemetry.power_draw_watts}W
                      </span>
                    </td>

                    {/* Region & Ping */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Globe className="w-3.5 h-3.5 text-slate-500" />
                        <div className="flex flex-col">
                          <span className="text-xs text-white">
                            {node.region}
                          </span>
                          <span className="text-xs text-slate-500 font-mono">
                            {node.ping_ms}ms
                          </span>
                        </div>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default NodeTelemetry;
