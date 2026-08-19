import React, { useEffect, useState } from 'react';
import {
  ArrowLeft,
  ChevronRight,
  Clapperboard,
  LoaderCircle,
  Plus,
  RefreshCw,
  TriangleAlert,
} from 'lucide-react';
import {
  isTerminalRenderStatus,
  listRenderJobs,
  RENDER_POLL_INTERVAL_MS,
} from '../../services/renderApi';
import {
  formatRenderDate,
  frameProgressText,
  RenderStatusBadge,
  renderStatusMessage,
} from './renderJobUi';

export default function RenderJobsPage({ onNavigate }) {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let mounted = true;
    let timerId = null;

    const loadJobs = async () => {
      try {
        const result = await listRenderJobs();
        if (!mounted) return;
        const nextJobs = result.jobs ?? [];
        setJobs(nextJobs);
        setError('');
        setLoading(false);

        if (nextJobs.some((job) => !isTerminalRenderStatus(job.status))) {
          timerId = window.setTimeout(loadJobs, RENDER_POLL_INTERVAL_MS);
        }
      } catch (requestError) {
        if (!mounted) return;
        setError(requestError.message);
        setLoading(false);
        timerId = window.setTimeout(loadJobs, RENDER_POLL_INTERVAL_MS);
      }
    };

    loadJobs();
    return () => {
      mounted = false;
      if (timerId !== null) window.clearTimeout(timerId);
    };
  }, [refreshKey]);

  const hasActiveJobs = jobs.some((job) => !isTerminalRenderStatus(job.status));

  return (
    <div className="mx-auto max-w-[1180px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
      <button type="button" onClick={() => onNavigate('/app/render')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 hover:text-white">
        <ArrowLeft className="h-3.5 w-3.5" /> Render workspace
      </button>

      <div className="mt-6 flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.22em] text-cyan-300"><Clapperboard className="h-3.5 w-3.5" /> Live render queue</div>
          <h1 className="mt-3 text-3xl font-medium tracking-[-0.035em] text-slate-100 sm:text-4xl">Render jobs</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">Track each batch by its real frame counts and open a job to inspect every frame.</p>
        </div>
        <div className="flex flex-wrap gap-3">
          <button type="button" onClick={() => setRefreshKey((value) => value + 1)} className="inline-flex items-center gap-2 rounded-lg border border-white/[0.09] px-4 py-2.5 text-[11px] text-slate-400 hover:text-white"><RefreshCw className="h-3.5 w-3.5" /> Refresh</button>
          <button type="button" onClick={() => onNavigate('/app/render')} className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-4 py-2.5 text-[11px] font-semibold text-[#08090a]"><Plus className="h-3.5 w-3.5" /> New render</button>
        </div>
      </div>

      {error && (
        <div className="mt-6 flex items-start gap-3 rounded-xl border border-red-300/20 bg-red-300/[0.04] p-4 text-red-100/70">
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-300" />
          <div><p className="text-xs font-medium">Render jobs could not be refreshed.</p><p className="mt-1 text-[11px] leading-5">{error}</p></div>
        </div>
      )}

      {loading ? (
        <div className="mt-6 flex min-h-64 flex-col items-center justify-center rounded-xl border border-white/[0.07] bg-white/[0.018] text-center">
          <LoaderCircle className="h-6 w-6 animate-spin text-cyan-300" />
          <p className="mt-4 text-xs text-slate-500">Loading render jobs…</p>
        </div>
      ) : jobs.length === 0 && !error ? (
        <div className="mt-6 flex min-h-72 flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.1] bg-white/[0.018] p-8 text-center">
          <Clapperboard className="h-7 w-7 text-slate-700" />
          <h2 className="mt-4 text-base font-medium text-slate-300">No render jobs yet</h2>
          <p className="mt-2 max-w-md text-[11px] leading-5 text-slate-600">The empty queue is normal during the pilot. Create a job when you have a packed Blender project ready.</p>
          <button type="button" onClick={() => onNavigate('/app/render')} className="mt-6 inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]"><Plus className="h-3.5 w-3.5" /> Create first render</button>
        </div>
      ) : jobs.length > 0 ? (
        <div className="mt-6 space-y-3">
          {jobs.map((job) => (
            <button key={job.job_id} type="button" onClick={() => onNavigate(`/app/render/jobs/${job.job_id}`)} className="group w-full rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 text-left transition-colors hover:border-cyan-300/20 hover:bg-cyan-300/[0.025] sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-3"><RenderStatusBadge status={job.status} /><span className="font-mono text-[9px] uppercase tracking-[0.16em] text-slate-700">{job.frame_count} frames · {job.output_format}</span></div>
                  <p className="mt-4 break-all font-mono text-xs text-slate-300">{job.job_id}</p>
                  <p className="mt-2 text-[11px] text-slate-600">Submitted {formatRenderDate(job.created_at)} · Blender {job.blender_version} · <span className="capitalize">{job.engine}</span></p>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-slate-700 transition-transform group-hover:translate-x-0.5 group-hover:text-cyan-300" />
              </div>
              <div className="mt-5 grid gap-3 border-t border-white/[0.06] pt-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <div><p className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Frame state</p><p className="mt-2 text-xs text-slate-300">{frameProgressText(job)}</p></div>
                <div><p className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">Current state</p><p className="mt-2 text-xs text-slate-400">{renderStatusMessage(job)}</p></div>
              </div>
            </button>
          ))}
        </div>
      ) : null}

      {hasActiveJobs && <p className="mt-4 text-right font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Refreshing every {RENDER_POLL_INTERVAL_MS / 1000}s while jobs are active</p>}
    </div>
  );
}
