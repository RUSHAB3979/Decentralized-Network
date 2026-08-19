import React, { useEffect, useRef, useState } from 'react';
import {
  ArrowLeft,
  Clock3,
  Download,
  FileArchive,
  LoaderCircle,
  RefreshCw,
  Square,
  TriangleAlert,
} from 'lucide-react';
import {
  cancelRenderJob,
  getRenderArtifacts,
  getRenderJob,
  isTerminalRenderStatus,
  RENDER_POLL_INTERVAL_MS,
} from '../../services/renderApi';
import {
  formatBytes,
  formatRenderDate,
  frameProgressText,
  RenderStatusBadge,
  renderStatusLabel,
  renderStatusMessage,
} from './renderJobUi';

const frameStatusStyle = (status) => ({
  completed: 'text-emerald-300',
  running: 'text-violet-300',
  failed: 'text-red-300',
  queued: 'text-cyan-300',
  cancelled: 'text-slate-500',
}[status] ?? 'text-amber-300');

const renderSeconds = (value) => {
  const seconds = Number(value);
  return Number.isFinite(seconds) ? `${seconds.toFixed(1)}s` : '—';
};

export default function RenderJobDetailPage({ jobId, onNavigate }) {
  const [job, setJob] = useState(null);
  const [artifacts, setArtifacts] = useState([]);
  const [artifactExpiry, setArtifactExpiry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [artifactError, setArtifactError] = useState('');
  const [cancelling, setCancelling] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    let mounted = true;

    const poll = async () => {
      try {
        const nextJob = await getRenderJob(jobId);
        if (!mounted) return;
        setJob(nextJob);
        setError('');
        setLoading(false);

        try {
          const artifactResult = await getRenderArtifacts(jobId);
          if (!mounted) return;
          setArtifacts(artifactResult.artifacts ?? []);
          setArtifactExpiry(artifactResult.expires_at ?? null);
          setArtifactError('');
        } catch (requestError) {
          if (!mounted) return;
          setArtifactError(requestError.message);
        }

        if (!isTerminalRenderStatus(nextJob.status)) {
          timerRef.current = window.setTimeout(poll, RENDER_POLL_INTERVAL_MS);
        }
      } catch (requestError) {
        if (!mounted) return;
        setError(requestError.message);
        setLoading(false);
        timerRef.current = window.setTimeout(poll, RENDER_POLL_INTERVAL_MS);
      }
    };

    poll();
    return () => {
      mounted = false;
      if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    };
  }, [jobId, refreshKey]);

  const cancel = async () => {
    const confirmed = window.confirm(
      'Cancel this render job? Frames already rendering will finish, and completed or in-flight work may still be billable.',
    );
    if (!confirmed) return;

    if (timerRef.current !== null) window.clearTimeout(timerRef.current);
    setCancelling(true);
    setError('');
    try {
      const cancelledJob = await cancelRenderJob(jobId);
      setJob(cancelledJob);
      setRefreshKey((value) => value + 1);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setCancelling(false);
    }
  };

  const artifactsByFrame = new Map(artifacts.map((artifact) => [artifact.frame_number, artifact]));
  const terminal = job ? isTerminalRenderStatus(job.status) : false;

  if (loading) {
    return (
      <div className="mx-auto flex min-h-[calc(100vh-72px)] max-w-5xl flex-col items-center justify-center px-6 text-center">
        <LoaderCircle className="h-7 w-7 animate-spin text-cyan-300" />
        <p className="mt-4 text-xs text-slate-500">Loading render job…</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-10 sm:px-7">
        <button type="button" onClick={() => onNavigate('/app/render/jobs')} className="flex items-center gap-2 text-[11px] text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> Render jobs</button>
        <div className="mt-8 rounded-xl border border-red-300/20 bg-red-300/[0.04] p-6 text-red-100/70"><TriangleAlert className="h-5 w-5 text-red-300" /><h1 className="mt-4 text-lg font-medium">Render job unavailable</h1><p className="mt-2 text-sm leading-6">{error}</p><button type="button" onClick={() => setRefreshKey((value) => value + 1)} className="mt-5 inline-flex items-center gap-2 rounded-lg border border-red-200/20 px-4 py-2.5 text-xs"><RefreshCw className="h-3.5 w-3.5" /> Retry</button></div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-[1180px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
      <button type="button" onClick={() => onNavigate('/app/render/jobs')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 hover:text-white"><ArrowLeft className="h-3.5 w-3.5" /> All render jobs</button>

      <section className="mt-6 rounded-2xl border border-white/[0.07] bg-[#0c0e16] p-6 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-3"><RenderStatusBadge status={job.status} />{!terminal && <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-slate-700">Refreshing every {RENDER_POLL_INTERVAL_MS / 1000}s</span>}</div>
            <h1 className="mt-4 break-all font-mono text-lg text-slate-100 sm:text-2xl">{job.job_id}</h1>
            <p className="mt-3 text-sm leading-6 text-slate-400">{renderStatusMessage(job)}</p>
          </div>
          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={() => setRefreshKey((value) => value + 1)} className="inline-flex items-center gap-2 rounded-lg border border-white/[0.09] px-4 py-2.5 text-[11px] text-slate-400 hover:text-white"><RefreshCw className="h-3.5 w-3.5" /> Refresh</button>
            {!terminal && <button type="button" disabled={cancelling} onClick={cancel} className="inline-flex items-center gap-2 rounded-lg border border-red-300/20 bg-red-300/[0.04] px-4 py-2.5 text-[11px] text-red-200/80 hover:text-red-100 disabled:opacity-50">{cancelling ? <LoaderCircle className="h-3.5 w-3.5 animate-spin" /> : <Square className="h-3.5 w-3.5" />}{cancelling ? 'Cancelling…' : 'Cancel job'}</button>}
          </div>
        </div>

        {error && <div className="mt-5 flex items-start gap-3 rounded-lg border border-red-300/20 bg-red-300/[0.04] p-4 text-[11px] leading-5 text-red-100/70"><TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-red-300" />{error}</div>}

        <div className="mt-7 grid gap-px overflow-hidden rounded-xl border border-white/[0.06] bg-white/[0.06] sm:grid-cols-2 lg:grid-cols-4">
          {[
            ['Frame progress', frameProgressText(job)],
            ['Configuration', `Blender ${job.blender_version} · ${job.engine}`],
            ['Output', `${job.output_format?.toUpperCase()} · frames ${job.frame_start}–${job.frame_end}`],
            ['Submitted', formatRenderDate(job.created_at)],
          ].map(([label, value]) => <div key={label} className="bg-[#0a0c12] p-5"><p className="font-mono text-[8px] uppercase tracking-[0.18em] text-slate-700">{label}</p><p className="mt-2 text-xs leading-5 text-slate-300">{value}</p></div>)}
        </div>
      </section>

      <div className="mt-5 grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="overflow-hidden rounded-xl border border-white/[0.07] bg-white/[0.018]">
          <div className="border-b border-white/[0.06] p-5 sm:flex sm:items-end sm:justify-between sm:gap-4">
            <div><h2 className="text-sm font-medium text-slate-200">Frames</h2><p className="mt-1 text-[11px] text-slate-600">Each row is independently claimed, rendered, and retried.</p></div>
            <p className="mt-3 font-mono text-[9px] text-slate-600 sm:mt-0">{job.frames?.length ?? 0} frame records</p>
          </div>

          {job.frames?.length ? (
            <div className="divide-y divide-white/[0.05]">
              {job.frames.map((frame) => {
                const artifact = artifactsByFrame.get(frame.frame_number);
                return (
                  <article key={frame.frame_number} className="grid gap-4 p-5 sm:grid-cols-[90px_minmax(0,1fr)_auto] sm:items-center">
                    <div><p className="font-mono text-[8px] uppercase tracking-[0.17em] text-slate-700">Frame</p><p className="mt-1 font-mono text-base text-slate-200">{frame.frame_number}</p></div>
                    <div>
                      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
                        <span className={`font-mono text-[9px] uppercase tracking-[0.16em] ${frameStatusStyle(frame.status)}`}>{renderStatusLabel(frame.status)}</span>
                        <span className="text-[10px] text-slate-600">Attempts: {frame.attempts}</span>
                        <span className="text-[10px] text-slate-600">Render time: {renderSeconds(frame.render_seconds)}</span>
                      </div>
                      {frame.error_code && <p className="mt-2 font-mono text-[9px] text-red-300/70">{frame.error_code}</p>}
                      {frame.completed_at && <p className="mt-2 text-[9px] text-slate-700">Completed {formatRenderDate(frame.completed_at)}</p>}
                    </div>
                    {artifact ? <a href={artifact.url} target="_blank" rel="noreferrer" download className="inline-flex items-center justify-center gap-2 rounded-lg border border-cyan-300/15 bg-cyan-300/[0.03] px-3 py-2.5 text-[10px] text-cyan-200 hover:bg-cyan-300/[0.06]"><Download className="h-3.5 w-3.5" /> Download · {formatBytes(artifact.bytes)}</a> : <span className="font-mono text-[8px] uppercase tracking-[0.14em] text-slate-800">No artifact yet</span>}
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="flex min-h-52 flex-col items-center justify-center p-8 text-center"><Clock3 className="h-6 w-6 text-slate-800" /><p className="mt-4 text-xs text-slate-500">{job.status === 'awaiting_upload' ? 'Frames are created only after the upload is confirmed.' : 'No frame records are available yet.'}</p></div>
          )}
        </section>

        <aside className="space-y-4">
          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5">
            <FileArchive className="h-5 w-5 text-cyan-300" />
            <h2 className="mt-4 text-sm font-medium text-slate-200">Job details</h2>
            <dl className="mt-4 space-y-3 text-[11px]">
              <div className="flex justify-between gap-4"><dt className="text-slate-600">Source size</dt><dd className="font-mono text-slate-300">{formatBytes(job.source_bytes)}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-slate-600">Spending limit</dt><dd className="font-mono text-slate-300">${Number(job.spending_limit_usd).toFixed(2)}</dd></div>
              <div className="flex justify-between gap-4"><dt className="text-slate-600">Uploaded</dt><dd className="text-right text-slate-300">{formatRenderDate(job.uploaded_at)}</dd></div>
            </dl>
          </section>

          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5">
            <Download className="h-5 w-5 text-emerald-300" />
            <h2 className="mt-4 text-sm font-medium text-slate-200">Artifacts</h2>
            <p className="mt-2 text-[11px] leading-5 text-slate-600">{artifacts.length ? `${artifacts.length} completed frame ${artifacts.length === 1 ? 'artifact' : 'artifacts'} available.` : 'Downloads appear beside completed frames.'}</p>
            {artifactExpiry && <p className="mt-3 text-[9px] leading-4 text-slate-700">Current signed links expire {formatRenderDate(artifactExpiry)}. Refresh to request new links.</p>}
            {artifactError && <p className="mt-3 rounded-lg border border-amber-300/15 bg-amber-300/[0.04] p-3 text-[10px] leading-5 text-amber-100/60">Artifact links could not be refreshed: {artifactError}</p>}
          </section>
        </aside>
      </div>
    </div>
  );
}
