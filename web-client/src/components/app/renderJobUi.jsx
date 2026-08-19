import React from 'react';
import { isTerminalRenderStatus } from '../../services/renderApi';

const STATUS_STYLES = {
  awaiting_upload: 'border-amber-300/20 bg-amber-300/[0.05] text-amber-300',
  queued: 'border-cyan-300/20 bg-cyan-300/[0.05] text-cyan-300',
  running: 'border-violet-300/20 bg-violet-300/[0.05] text-violet-300',
  completed: 'border-emerald-300/20 bg-emerald-300/[0.05] text-emerald-300',
  failed: 'border-red-300/20 bg-red-300/[0.05] text-red-300',
  cancelled: 'border-slate-400/20 bg-slate-400/[0.05] text-slate-400',
};

export const renderStatusLabel = (status) => ({
  awaiting_upload: 'Awaiting upload',
  queued: 'Queued',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}[status] ?? status?.replaceAll('_', ' ') ?? 'Unknown');

export const RenderStatusBadge = ({ status }) => (
  <span className={`inline-flex rounded-full border px-3 py-1.5 font-mono text-[8px] uppercase tracking-[0.17em] ${STATUS_STYLES[status] ?? STATUS_STYLES.cancelled}`}>
    {renderStatusLabel(status)}
  </span>
);

export function frameProgressText(job) {
  const completed = job?.frames_completed ?? 0;
  const total = job?.frame_count ?? 0;
  const failed = job?.frames_failed ?? 0;
  const running = job?.frames_running ?? 0;
  const parts = [`${completed} of ${total} done`];

  if (failed) {
    parts.push(`${failed} failed${isTerminalRenderStatus(job?.status) ? '' : ' and retrying'}`);
  }
  if (running) parts.push(`${running} rendering now`);
  return parts.join(', ');
}

export function renderStatusMessage(job) {
  if (job?.status === 'awaiting_upload') return 'Waiting for the project file to finish uploading.';
  if (job?.status === 'queued') return 'Waiting for an available renderer.';
  if (job?.status === 'running') return frameProgressText(job);
  if (job?.status === 'completed') return 'Every frame reached a completed state.';
  if (job?.status === 'failed') return job.error_code ? `Render failed: ${job.error_code}` : 'The render could not be completed.';
  if (job?.status === 'cancelled') return 'This job was cancelled. Frames already rendering may still finish.';
  return 'Render status is not available.';
}

export function formatRenderDate(value) {
  if (!value) return 'Not available';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}

export function formatBytes(value) {
  const bytes = Number(value);
  if (!Number.isFinite(bytes) || bytes < 0) return 'Not available';
  if (bytes < 1024) return `${bytes} B`;
  const units = ['KB', 'MB', 'GB', 'TB'];
  let size = bytes / 1024;
  let unit = units[0];
  for (let index = 1; size >= 1024 && index < units.length; index += 1) {
    size /= 1024;
    unit = units[index];
  }
  return `${size >= 10 ? size.toFixed(1) : size.toFixed(2)} ${unit}`;
}
