import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  ChevronRight,
  Clapperboard,
  Cpu,
  FileArchive,
  Film,
  HardDriveUpload,
  Info,
  List,
  LoaderCircle,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from 'lucide-react';
import {
  confirmRenderUpload,
  createRenderJob,
  reissueRenderUploadUrl,
  uploadRenderSource,
} from '../../services/renderApi';
import {
  formatBytes,
  RenderStatusBadge,
  renderStatusMessage,
} from './renderJobUi';

const GPU_PROFILES = [
  { id: 'balanced', label: 'Balanced', gpu: '12–16 GB VRAM' },
  { id: 'performance', label: 'Performance', gpu: '20–24 GB VRAM' },
  { id: 'maximum', label: 'Maximum', gpu: '40+ GB VRAM' },
];

const INITIAL_SUBMISSION = {
  phase: 'idle',
  failedStep: null,
  error: '',
  job: null,
  upload: { loaded: 0, total: 0, percent: 0 },
};

const SubmissionState = ({ submission, file, onNavigate, onReset, onRetryConfirmation, onRetryUpload }) => {
  const { phase, failedStep, error, job, upload } = submission;
  const uploading = phase === 'uploading';
  const confirming = phase === 'confirming';
  const complete = phase === 'complete';
  const failed = phase === 'error';
  const uploadFailed = failed && failedStep === 'upload';
  const confirmationFailed = failed && failedStep === 'confirmation';

  const title = uploadFailed
    ? 'The project upload did not complete.'
    : confirmationFailed
      ? 'The upload confirmation needs attention.'
      : complete
        ? 'Your render job is in the queue.'
        : uploading
          ? 'Uploading your project directly to storage.'
          : 'Confirming the uploaded project.';

  return (
    <div className="mx-auto max-w-4xl px-4 py-10 sm:px-7 lg:py-16">
      <div className={`relative overflow-hidden rounded-2xl border bg-[#0c0f14] p-7 sm:p-10 ${failed ? 'border-amber-300/20' : 'border-emerald-300/15'}`}>
        <div className="pointer-events-none absolute right-0 top-0 h-72 w-72 rounded-full bg-emerald-400/[0.08] blur-[100px]" />
        <div className="relative">
          <span className={`flex h-12 w-12 items-center justify-center rounded-xl border ${failed ? 'border-amber-300/20 bg-amber-300/[0.06] text-amber-300' : 'border-emerald-300/20 bg-emerald-300/[0.06] text-emerald-300'}`}>
            {failed ? <TriangleAlert className="h-6 w-6" /> : complete ? <CheckCircle2 className="h-6 w-6" /> : <LoaderCircle className="h-6 w-6 animate-spin" />}
          </span>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <p className="font-mono text-[9px] uppercase tracking-[0.24em] text-emerald-300">Live render job</p>
            <RenderStatusBadge status={job.status} />
          </div>
          <h1 className="mt-3 text-3xl font-medium tracking-[-0.035em] text-slate-100 sm:text-4xl">{title}</h1>

          {failed ? (
            <p className="mt-4 max-w-2xl rounded-lg border border-amber-300/15 bg-amber-300/[0.04] p-4 text-sm leading-6 text-amber-100/70">{error}</p>
          ) : (
            <p className="mt-4 max-w-2xl text-sm leading-7 text-slate-400">
              {complete ? renderStatusMessage(job) : uploading ? 'Keep this tab open until the file reaches 100%.' : 'The orchestrator is verifying the object and creating one work item per frame.'}
            </p>
          )}

          {(uploading || confirming || uploadFailed) && (
            <div className="mt-7 rounded-xl border border-white/[0.07] bg-black/20 p-5">
              <div className="flex items-center justify-between gap-4 text-xs">
                <span className="text-slate-500">Project upload</span>
                <span className="font-mono text-slate-200">{upload.percent}%</span>
              </div>
              <div className="mt-3 h-2 overflow-hidden rounded-full bg-white/[0.06]" role="progressbar" aria-label="Project upload progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow={upload.percent}>
                <div className={`h-full rounded-full ${uploadFailed ? 'bg-amber-300' : 'bg-cyan-300'}`} style={{ width: `${upload.percent}%` }} />
              </div>
              <p className="mt-2 text-right font-mono text-[9px] text-slate-600">{formatBytes(upload.loaded)} of {formatBytes(upload.total || file?.size)}</p>
            </div>
          )}

          <dl className="mt-8 grid gap-3 rounded-xl border border-white/[0.07] bg-black/20 p-5 sm:grid-cols-2">
            <div><dt className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Project</dt><dd className="mt-1.5 truncate text-sm text-slate-200">{file?.name}</dd></div>
            <div><dt className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Job ID</dt><dd className="mt-1.5 break-all font-mono text-sm text-cyan-200">{job.job_id}</dd></div>
            <div><dt className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Workload</dt><dd className="mt-1.5 text-sm capitalize text-slate-200">Blender {job.blender_version} · {job.engine}</dd></div>
            <div><dt className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Frame range</dt><dd className="mt-1.5 text-sm text-slate-200">{job.frame_start}–{job.frame_end} · {job.frame_count} frames</dd></div>
          </dl>

          {uploadFailed && (
            <p className="mt-4 text-[11px] leading-5 text-slate-500">This job is still <span className="font-mono text-amber-300">awaiting_upload</span>. It has not been fanned out to renderers.</p>
          )}

          <div className="mt-8 flex flex-wrap gap-3">
            {(complete || failed) && <button type="button" onClick={() => onNavigate(`/app/render/jobs/${job.job_id}`)} className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]">View job details <ChevronRight className="h-3.5 w-3.5" /></button>}
            {uploadFailed && file && <button type="button" onClick={onRetryUpload} className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]"><RotateCcw className="h-3.5 w-3.5" /> Retry upload</button>}
            {confirmationFailed && <button type="button" onClick={onRetryConfirmation} className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-5 py-3 text-xs font-semibold text-[#08090a]"><RotateCcw className="h-3.5 w-3.5" /> Retry confirmation</button>}
            {(complete || failed) && <button type="button" onClick={onReset} className="inline-flex items-center gap-2 rounded-lg border border-white/[0.09] bg-white/[0.025] px-5 py-3 text-xs font-semibold text-slate-300 hover:text-white"><RotateCcw className="h-3.5 w-3.5" /> Create another job</button>}
            <button type="button" onClick={() => onNavigate('/app/render/jobs')} className="inline-flex items-center gap-2 rounded-lg border border-white/[0.09] bg-white/[0.025] px-5 py-3 text-xs font-semibold text-slate-300 hover:text-white"><List className="h-3.5 w-3.5" /> All render jobs</button>
          </div>
        </div>
      </div>
    </div>
  );
};

const RenderJobPage = ({ onNavigate }) => {
  const [file, setFile] = useState(null);
  const [engine, setEngine] = useState('cycles');
  const [version, setVersion] = useState('4.3');
  const [gpuProfile, setGpuProfile] = useState('balanced');
  const [region, setRegion] = useState('auto');
  const [frameStart, setFrameStart] = useState(1);
  const [frameEnd, setFrameEnd] = useState(120);
  const [output, setOutput] = useState('png');
  const [spendingLimit, setSpendingLimit] = useState('5.00');
  const [submission, setSubmission] = useState(INITIAL_SUBMISSION);
  const uploadController = useRef(null);

  useEffect(() => () => uploadController.current?.abort(), []);

  const quote = useMemo(() => {
    const profile = GPU_PROFILES.find((item) => item.id === gpuProfile) || GPU_PROFILES[0];
    const start = Number(frameStart) || 1;
    const end = Number(frameEnd) || start;
    return { profile, frameCount: Math.max(1, end - start + 1) };
  }, [frameStart, frameEnd, gpuProfile]);

  const submit = async (event) => {
    event.preventDefault();
    if (!file) return;

    const start = Number(frameStart);
    const end = Number(frameEnd);
    const limit = Number(spendingLimit);
    const supportedOutput = output === 'png' || output === 'exr';
    const supportedEngine = engine === 'cycles' || engine === 'eevee';
    if (!Number.isInteger(start) || start < 1 || !Number.isInteger(end) || end < start || !Number.isFinite(limit) || limit < 0.1 || !supportedOutput || !supportedEngine) {
      setSubmission({ ...INITIAL_SUBMISSION, phase: 'error', failedStep: 'create', error: 'Check the frame range, render engine, output format, and spending limit, then try again.' });
      return;
    }

    let createdJob = null;
    let uploadFinished = false;
    setSubmission({ ...INITIAL_SUBMISSION, phase: 'creating' });

    try {
      const payload = {
        blender_version: version,
        engine,
        frame_start: start,
        frame_end: end,
        output_format: output,
        source_bytes: file.size,
        spending_limit_usd: limit,
      };
      // The 202 response intentionally contains only upload coordination data.
      // Retain the submitted fields locally so the in-progress and failed-upload
      // states can still describe the job before the full view is available.
      createdJob = { ...payload, ...await createRenderJob(payload) };
      setSubmission({
        ...INITIAL_SUBMISSION,
        phase: 'uploading',
        job: createdJob,
        upload: { loaded: 0, total: file.size, percent: 0 },
      });
      window.scrollTo({ top: 0, behavior: 'smooth' });

      uploadController.current = new AbortController();
      await uploadRenderSource(createdJob.upload_url, file, {
        expiresAt: createdJob.upload_expires_at,
        signal: uploadController.current.signal,
        onProgress: (progress) => setSubmission((current) => ({ ...current, upload: progress })),
      });
      uploadFinished = true;
      setSubmission((current) => ({
        ...current,
        phase: 'confirming',
        upload: { loaded: file.size, total: file.size, percent: 100 },
      }));

      const confirmedJob = await confirmRenderUpload(createdJob.job_id);
      setSubmission((current) => ({ ...current, phase: 'complete', job: confirmedJob }));
    } catch (requestError) {
      setSubmission((current) => ({
        ...current,
        phase: 'error',
        failedStep: createdJob ? (uploadFinished ? 'confirmation' : 'upload') : 'create',
        error: requestError.message,
        job: createdJob ?? current.job,
      }));
    } finally {
      uploadController.current = null;
    }
  };

  // The job survives a failed upload; only the signature expired. Asking for a
  // fresh one keeps the same job_id, frame range and object key, so a slow
  // connection costs a retry rather than a second orphaned job row.
  const retryUpload = async () => {
    const job = submission.job;
    if (!job || !file) return;
    let uploadFinished = false;
    setSubmission((current) => ({
      ...current,
      phase: 'uploading',
      error: '',
      failedStep: null,
      upload: { loaded: 0, total: file.size, percent: 0 },
    }));
    try {
      const refreshed = await reissueRenderUploadUrl(job.job_id);
      uploadController.current = new AbortController();
      await uploadRenderSource(refreshed.upload_url, file, {
        expiresAt: refreshed.upload_expires_at,
        signal: uploadController.current.signal,
        onProgress: (progress) => setSubmission((current) => ({ ...current, upload: progress })),
      });
      uploadFinished = true;
      setSubmission((current) => ({
        ...current,
        phase: 'confirming',
        upload: { loaded: file.size, total: file.size, percent: 100 },
      }));
      const confirmedJob = await confirmRenderUpload(job.job_id);
      setSubmission((current) => ({ ...current, phase: 'complete', job: confirmedJob }));
    } catch (requestError) {
      setSubmission((current) => ({
        ...current,
        phase: 'error',
        failedStep: uploadFinished ? 'confirmation' : 'upload',
        error: requestError.message,
      }));
    } finally {
      uploadController.current = null;
    }
  };

  const retryConfirmation = async () => {
    if (!submission.job) return;
    setSubmission((current) => ({ ...current, phase: 'confirming', error: '', failedStep: null }));
    try {
      const confirmedJob = await confirmRenderUpload(submission.job.job_id);
      setSubmission((current) => ({ ...current, phase: 'complete', job: confirmedJob }));
    } catch (requestError) {
      setSubmission((current) => ({ ...current, phase: 'error', failedStep: 'confirmation', error: requestError.message }));
    }
  };

  const reset = () => {
    uploadController.current?.abort();
    setSubmission(INITIAL_SUBMISSION);
    setFile(null);
    setFrameStart(1);
    setFrameEnd(120);
  };

  if (submission.job) {
    return <SubmissionState submission={submission} file={file} onNavigate={onNavigate} onReset={reset} onRetryConfirmation={retryConfirmation} onRetryUpload={retryUpload} />;
  }

  const creating = submission.phase === 'creating';

  return (
    <div className="mx-auto max-w-[1380px] px-4 py-7 sm:px-7 lg:px-9 lg:py-10">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <button type="button" onClick={() => onNavigate('/app')} className="flex items-center gap-2 text-[11px] font-medium text-slate-500 transition-colors hover:text-white">
          <ArrowLeft className="h-3.5 w-3.5" /> Marketplace overview
        </button>
        <button type="button" onClick={() => onNavigate('/app/render/jobs')} className="flex items-center gap-2 text-[11px] font-medium text-cyan-300/80 transition-colors hover:text-cyan-200">
          <List className="h-3.5 w-3.5" /> View render jobs
        </button>
      </div>

      <div className="mt-6 flex flex-wrap items-end justify-between gap-5">
        <div>
          <div className="flex items-center gap-2 font-mono text-[9px] uppercase tracking-[0.22em] text-cyan-300">
            <Clapperboard className="h-3.5 w-3.5" /> Render workspace
          </div>
          <h1 className="mt-3 text-3xl font-medium tracking-[-0.035em] text-slate-100 sm:text-4xl">Create a Blender render job</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-500">Create the job, upload the project straight to signed object storage, then fan it out into one work item per frame.</p>
        </div>
        <span className="rounded-full border border-emerald-300/15 bg-emerald-300/[0.04] px-3 py-1.5 font-mono text-[8px] uppercase tracking-[0.2em] text-emerald-300">Live API · direct upload</span>
      </div>

      <form onSubmit={submit} className="mt-8 grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-cyan-300/15 bg-cyan-300/[0.04] text-cyan-300"><HardDriveUpload className="h-4 w-4" /></span>
              <div><h2 className="text-sm font-medium text-slate-100">Project file</h2><p className="mt-1 text-[11px] text-slate-600">Use a packed Blender project with all external assets included.</p></div>
            </div>
            <label className="mt-5 flex min-h-44 cursor-pointer flex-col items-center justify-center rounded-xl border border-dashed border-white/[0.12] bg-black/15 px-5 text-center transition-colors hover:border-cyan-300/30 hover:bg-cyan-300/[0.025]">
              <input type="file" accept=".blend,.zip" required className="sr-only" onChange={(event) => setFile(event.target.files?.[0] || null)} />
              <FileArchive className="h-7 w-7 text-slate-600" />
              <p className="mt-3 text-sm font-medium text-slate-300">{file ? file.name : 'Choose a .blend or .zip project'}</p>
              <p className="mt-1 text-[11px] text-slate-600">{file ? `${formatBytes(file.size)} · ready for direct upload` : 'The selected file uploads directly to signed object storage'}</p>
            </label>
          </section>

          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-violet-300/15 bg-violet-300/[0.04] text-violet-300"><Film className="h-4 w-4" /></span>
              <div><h2 className="text-sm font-medium text-slate-100">Render configuration</h2><p className="mt-1 text-[11px] text-slate-600">These values are validated again by the render API.</p></div>
            </div>

            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              <label className="app-field"><span>Blender version</span><select value={version} onChange={(event) => setVersion(event.target.value)}><option value="4.3">Blender 4.3 LTS</option><option value="4.2">Blender 4.2 LTS</option><option value="3.6">Blender 3.6 LTS</option></select></label>
              <label className="app-field"><span>Render engine</span><select value={engine} onChange={(event) => setEngine(event.target.value)}><option value="cycles">Cycles</option><option value="eevee">Eevee</option></select></label>
              <label className="app-field"><span>Start frame</span><input type="number" min="1" step="1" value={frameStart} onChange={(event) => setFrameStart(event.target.value)} required /></label>
              <label className="app-field"><span>End frame</span><input type="number" min={frameStart || 1} step="1" value={frameEnd} onChange={(event) => setFrameEnd(event.target.value)} required /></label>
              <label className="app-field"><span>Output format</span><select value={output} onChange={(event) => setOutput(event.target.value)}><option value="png">PNG sequence</option><option value="exr">OpenEXR sequence</option><option value="mp4" disabled>MP4 video · not available yet</option></select></label>
              <label className="app-field"><span>Region preference · Preview</span><select value={region} onChange={(event) => setRegion(event.target.value)}><option value="auto">Auto · best value</option><option value="india">India</option><option value="asia">Asia Pacific</option><option value="global">Global</option></select></label>
            </div>
            <p className="mt-4 text-[10px] leading-5 text-slate-600">Region is a preview preference and is not part of the current render-job API contract. MP4 stays disabled until frame muxing exists.</p>
          </section>

          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5 sm:p-6">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-3">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-amber-300/15 bg-amber-300/[0.04] text-amber-300"><Cpu className="h-4 w-4" /></span>
                <div><h2 className="text-sm font-medium text-slate-100">GPU profile</h2><p className="mt-1 text-[11px] text-slate-600">A preference preview; the current API does not send it to the scheduler.</p></div>
              </div>
              <span className="font-mono text-[8px] uppercase tracking-[0.16em] text-amber-300">Preview</span>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-3">
              {GPU_PROFILES.map((profile) => (
                <button key={profile.id} type="button" onClick={() => setGpuProfile(profile.id)} className={`rounded-xl border p-4 text-left transition-all ${gpuProfile === profile.id ? 'border-cyan-300/30 bg-cyan-300/[0.045]' : 'border-white/[0.07] bg-black/10 hover:border-white/[0.13]'}`}>
                  <div className="flex items-center justify-between gap-3"><p className="text-xs font-medium text-slate-200">{profile.label}</p>{gpuProfile === profile.id && <CheckCircle2 className="h-3.5 w-3.5 text-cyan-300" />}</div>
                  <p className="mt-2 font-mono text-[9px] text-slate-600">{profile.gpu}</p>
                  <p className="mt-4 font-mono text-[8px] uppercase tracking-[0.15em] text-slate-700">Preview preference</p>
                </button>
              ))}
            </div>
          </section>
        </div>

        <aside className="space-y-5 xl:sticky xl:top-[92px] xl:self-start">
          <section className="rounded-xl border border-white/[0.08] bg-[#0d0f17] p-5">
            <div className="flex items-center justify-between"><h2 className="text-sm font-medium text-slate-100">Preview quote</h2><Sparkles className="h-4 w-4 text-indigo-300" /></div>
            <div className="mt-5 space-y-3 border-y border-white/[0.06] py-4 text-xs">
              <div className="flex justify-between gap-4"><span className="text-slate-600">Frames</span><span className="font-mono text-slate-300">{quote.frameCount}</span></div>
              <div className="flex justify-between gap-4"><span className="text-slate-600">GPU profile · Preview</span><span className="text-right text-slate-300">{quote.profile.label}</span></div>
              <div className="flex justify-between gap-4"><span className="text-slate-600">Output</span><span className="uppercase text-slate-300">{output}</span></div>
            </div>
            <div className="mt-5 flex items-end justify-between gap-4">
              <div><p className="font-mono text-[8px] uppercase tracking-[0.2em] text-slate-600">Estimated cost · Preview</p><p className="mt-1 text-xl font-medium tracking-[-0.02em] text-slate-300">Not available</p></div>
              <span className="pb-1 text-[9px] text-slate-700">Illustrative only</span>
            </div>
            <p className="mt-3 text-[10px] leading-5 text-slate-600">No metering is implemented, so this page cannot produce a price or time estimate.</p>
            <label className="app-field mt-5"><span>Hard spending limit</span><div className="relative"><span className="absolute left-3 top-1/2 -translate-y-1/2 text-xs text-slate-600">$</span><input type="number" min="0.10" step="0.10" value={spendingLimit} onChange={(event) => setSpendingLimit(event.target.value)} className="!pl-7" required /></div></label>
            <button type="submit" disabled={!file || creating} className="group mt-5 flex w-full items-center justify-center gap-2 rounded-lg bg-slate-100 px-4 py-3 text-xs font-semibold text-[#08090a] transition-all hover:bg-white disabled:cursor-not-allowed disabled:opacity-35">
              {creating ? <><LoaderCircle className="h-3.5 w-3.5 animate-spin" /> Creating job…</> : <>Submit render job <ChevronRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" /></>}
            </button>
            {!file && <p className="mt-2 text-center text-[10px] text-slate-700">Choose a project file to continue.</p>}
            {submission.phase === 'error' && submission.failedStep === 'create' && <p className="mt-3 rounded-lg border border-red-300/20 bg-red-300/[0.04] p-3 text-[11px] leading-5 text-red-200/70">{submission.error}</p>}
          </section>

          <section className="rounded-xl border border-white/[0.07] bg-white/[0.018] p-5">
            <div className="flex gap-3"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" /><div><p className="text-xs font-medium text-slate-300">Pilot safety boundary</p><p className="mt-2 text-[11px] leading-5 text-slate-600">Only explicitly render-eligible nodes can receive these jobs. That rollout gate limits the pilot; it is not a workload sandbox.</p></div></div>
            <div className="mt-4 flex gap-3 border-t border-white/[0.05] pt-4"><Info className="mt-0.5 h-4 w-4 shrink-0 text-slate-600" /><p className="text-[10px] leading-5 text-slate-600">Final quotes must come from live capacity, real metering, and backend-enforced policies.</p></div>
          </section>
        </aside>
      </form>
    </div>
  );
};

export default RenderJobPage;
