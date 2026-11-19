import React, { useEffect, useState } from 'react';
import { ArrowLeft, ClipboardList, KeyRound, LogOut, Server, WalletCards } from 'lucide-react';
import Logo from '../Logo';
import { useProviderSession } from '../../hooks/useProviderSession';
import {
  fetchEnrolmentKeys,
  fetchOwnedNodes,
  fetchProviderJobs,
  mintEnrolmentKey,
  revokeEnrolmentKey,
  revokeOwnedNode,
} from '../../services/providerAuthApi';

const PANEL = 'rounded-xl border border-white/10 bg-[#0d111a] p-5 sm:p-7';
const BUTTON = 'inline-flex items-center justify-center gap-2 rounded-lg border border-white/15 px-3 py-2 text-sm font-medium text-slate-100 hover:bg-white/8 disabled:opacity-50';
const PRIMARY = 'inline-flex items-center justify-center gap-2 rounded-lg bg-emerald-300 px-4 py-2 text-sm font-semibold text-emerald-950 hover:bg-emerald-200 disabled:opacity-50';
const INPUT = 'mt-2 w-full rounded-lg border border-white/15 bg-[#080b12] px-3 py-2.5 text-sm text-white focus:border-emerald-300 focus:outline-none';
const TABS = [
  { label: 'Machines', icon: Server },
  { label: 'Enrolment keys', icon: KeyRound },
  { label: 'Jobs', icon: ClipboardList },
  { label: 'Earnings', icon: WalletCards },
];

function formatTime(value) {
  return new Date(value).toLocaleString();
}

function useProviderCollection(fetchItems, token, invalidate) {
  const [revision, setRevision] = useState(0);
  const [result, setResult] = useState({ items: null, error: '' });
  useEffect(() => {
    const controller = new AbortController();
    let timer;
    async function load() {
      try {
        const items = await fetchItems(token, controller.signal);
        if (!controller.signal.aborted) setResult({ items, error: '' });
      } catch (error) {
        if (controller.signal.aborted) return;
        if (error.status === 401) {
          invalidate(token);
          return;
        }
        setResult((previous) => ({ ...previous, error: error.message }));
      }
      if (!controller.signal.aborted) timer = window.setTimeout(load, 15_000);
    }
    load();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [fetchItems, token, invalidate, revision]);
  return { ...result, refresh: () => setRevision((value) => value + 1) };
}

function ProviderSignIn({ mode, authenticate }) {
  const signup = mode === 'signup';
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function submit(event) {
    event.preventDefault();
    const fields = new FormData(event.currentTarget);
    setBusy(true);
    setError('');
    try {
      await authenticate(mode, {
        email: String(fields.get('email') ?? ''),
        password: String(fields.get('password') ?? ''),
        displayName: String(fields.get('displayName') ?? ''),
      });
    } catch (failure) {
      setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={PANEL + ' mx-auto w-full max-w-md'}>
      <h1 className="text-2xl font-semibold tracking-tight">
        {signup ? 'Create a provider account' : 'Sign in to the provider console'}
      </h1>
      <p className="mt-2 text-sm leading-6 text-slate-400">
        Use your provider account to enrol and manage your machines.
      </p>
      <form className="mt-6 grid gap-4" onSubmit={submit}>
        {signup && (
          <label className="block text-sm font-medium">
            Display name
            <input className={INPUT} name="displayName" autoComplete="nickname" maxLength={80} />
          </label>
        )}
        <label className="block text-sm font-medium">
          Email address
          <input className={INPUT} name="email" type="email" autoComplete="username" required maxLength={254} />
        </label>
        <label className="block text-sm font-medium">
          Password
          <input
            className={INPUT}
            name="password"
            type="password"
            autoComplete={signup ? 'new-password' : 'current-password'}
            minLength={signup ? 10 : 1}
            maxLength={256}
            required
          />
        </label>
        {error && <p role="alert" className="text-sm text-red-300">{error}</p>}
        <button className={PRIMARY + ' w-full'} type="submit" disabled={busy}>
          {busy ? 'Please wait…' : signup ? 'Create provider account' : 'Sign in'}
        </button>
      </form>
      <a className="mt-5 inline-block text-sm font-medium text-emerald-300 hover:underline" href={signup ? '#/provider/login' : '#/provider/signup'}>
        {signup ? 'Sign in to an existing provider account' : 'Create a provider account'}
      </a>
    </section>
  );
}

function RevokeControl({ label, onConfirm, disabled }) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <div className="flex flex-wrap gap-2" role="group" aria-label={label}>
        <button className={BUTTON + ' border-red-300/35 text-red-200'} type="button" disabled={disabled} onClick={() => {
          setConfirming(false);
          onConfirm();
        }}>Confirm revoke</button>
        <button className={BUTTON} type="button" disabled={disabled} onClick={() => setConfirming(false)}>Cancel</button>
      </div>
    );
  }
  return (
    <button className={BUTTON} type="button" aria-label={label} disabled={disabled} onClick={() => setConfirming(true)}>
      Revoke
    </button>
  );
}

function MachinesPanel({ token, invalidate, onEnrol }) {
  const nodes = useProviderCollection(fetchOwnedNodes, token, invalidate);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);

  async function revoke(nodeId) {
    setBusy(true);
    setMessage(null);
    try {
      await revokeOwnedNode(token, nodeId);
      setMessage({ text: 'Machine credential revoked.' });
      nodes.refresh();
    } catch (error) {
      if (error.status === 401) invalidate(token);
      else setMessage({ error: true, text: error.message });
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className={PANEL}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Your machines</h2>
          <p className="mt-1 text-sm text-slate-400">Review heartbeat and work approval for machines in this account.</p>
        </div>
        <button className={BUTTON} type="button" onClick={nodes.refresh}>Refresh</button>
      </div>
      {nodes.error && <p className="mt-4 text-sm text-red-300" role="alert">{nodes.error}</p>}
      {message && <p className={`mt-4 text-sm ${message.error ? 'text-red-300' : 'text-emerald-300'}`} role={message.error ? 'alert' : 'status'}>{message.text}</p>}
      {!nodes.items && !nodes.error && <p className="mt-6 text-sm text-slate-400" role="status">Loading machines…</p>}
      {nodes.items?.length === 0 && (
        <div className="mt-5 rounded-lg border border-dashed border-white/15 p-5">
          <p className="text-sm text-slate-300">This account has no enrolled machines.</p>
          <button className={PRIMARY + ' mt-3'} type="button" onClick={onEnrol}>Set up a machine</button>
        </div>
      )}
      {!!nodes.items?.length && (
        <ul className="mt-5 grid gap-3">
          {nodes.items.map((node) => {
            const name = node.hostname || node.node_id;
            const state = node.revoked_at ? 'Revoked' : node.inference_eligible || node.render_eligible ? 'Approved' : 'Awaiting approval';
            const heartbeat = node.liveness === 'online' ? 'Online' : node.liveness === 'offline' ? 'Offline' : 'No heartbeat yet';
            return (
              <li key={node.node_id} className="flex flex-wrap items-start justify-between gap-4 rounded-lg border border-white/10 bg-[#090d14] p-4">
                <div className="min-w-0 flex-1 basis-56">
                  <h3 className="wrap-anywhere text-sm font-semibold">{name}</h3>
                  {node.hostname && <p className="mt-1 wrap-anywhere font-mono text-xs text-slate-400">{node.node_id}</p>}
                  <p className="mt-2 text-sm text-slate-300">
                    {state}{!node.revoked_at && ` · ${heartbeat}`}
                  </p>
                  {node.last_heartbeat_at && (
                    <p className="mt-1 text-xs text-slate-400">Last heartbeat {formatTime(node.last_heartbeat_at)}</p>
                  )}
                  {!node.revoked_at && (node.inference_eligible || node.render_eligible) && (
                    <p className="mt-1 text-xs text-slate-400">
                      {[node.inference_eligible && 'Inference', node.render_eligible && 'Render'].filter(Boolean).join(', ')}
                      {node.liveness === 'online' && (node.accepts_work ? ' · Accepting work' : ' · Work paused')}
                    </p>
                  )}
                  {node.liveness === 'online' && !node.revoked_at && (
                    <p className="mt-2 wrap-anywhere text-xs text-slate-300">
                      {[
                        node.gpu_name,
                        node.vram_total_mb != null && `${node.vram_total_mb} MB VRAM`,
                        node.gpu_utilisation_pct != null && `${node.gpu_utilisation_pct}% GPU load`,
                        node.temperature_c != null && `${node.temperature_c} °C`,
                        node.ollama_reachable ? 'Ollama reachable' : 'Ollama unavailable',
                      ].filter(Boolean).join(' · ')}
                    </p>
                  )}
                </div>
                {!node.revoked_at && (
                  <RevokeControl label={`Revoke machine ${name}`} disabled={busy} onConfirm={() => revoke(node.node_id)} />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function EnrolmentPanel({ token, invalidate }) {
  const keys = useProviderCollection(fetchEnrolmentKeys, token, invalidate);
  const [issued, setIssued] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [copied, setCopied] = useState(false);

  async function issue() {
    setBusy(true);
    setError('');
    setCopied(false);
    try {
      const created = await mintEnrolmentKey(token);
      setIssued(created);
      keys.refresh();
    } catch (failure) {
      if (failure.status === 401) invalidate(token);
      else setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  async function revoke(keyId) {
    setBusy(true);
    setError('');
    try {
      await revokeEnrolmentKey(token, keyId);
      setIssued((current) => current?.enrolment_key_id === keyId ? null : current);
      keys.refresh();
    } catch (failure) {
      if (failure.status === 401) invalidate(token);
      else setError(failure.message);
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(issued.key);
      setCopied(true);
    } catch {
      setError('Clipboard is unavailable. Select and copy the key manually.');
    }
  }

  return (
    <section className={PANEL}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="max-w-xl">
          <h2 className="text-lg font-semibold">Enrolment keys</h2>
          <p className="mt-1 text-sm leading-6 text-slate-400">Generate a key, then paste it into the Windows provider app. Each key expires after 15 minutes and can be used once.</p>
        </div>
        <button className={PRIMARY} type="button" onClick={issue} disabled={busy || Boolean(issued)}>Generate key</button>
      </div>
      {error && <p className="mt-4 text-sm text-red-300" role="alert">{error}</p>}
      {issued && (
        <div className="mt-5 rounded-lg border border-emerald-300/25 bg-emerald-300/5 p-4">
          <label htmlFor="issued-enrolment-key" className="block text-sm font-semibold">One-time enrolment key</label>
          <p className="mt-1 text-sm text-slate-300">Copy it now. The console only shows the full key once.</p>
          <input className={INPUT + ' font-mono'} id="issued-enrolment-key" value={issued.key} readOnly autoComplete="off" onFocus={(event) => event.currentTarget.select()} />
          <div className="mt-3 flex flex-wrap gap-2">
            <button className={BUTTON} type="button" onClick={copy}>{copied ? 'Copied' : 'Copy key'}</button>
            <button className={BUTTON} type="button" onClick={() => setIssued(null)}>Hide key</button>
          </div>
        </div>
      )}
      <div className="mt-6 flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">Key history</h3>
        <button className={BUTTON} type="button" onClick={keys.refresh}>Refresh</button>
      </div>
      {keys.error && <p className="mt-4 text-sm text-red-300" role="alert">{keys.error}</p>}
      {!keys.items && !keys.error && <p className="mt-4 text-sm text-slate-400" role="status">Loading keys…</p>}
      {keys.items?.length === 0 && <p className="mt-4 text-sm text-slate-400">No keys generated yet.</p>}
      {!!keys.items?.length && (
        <ul className="mt-3 grid gap-2">
          {keys.items.map((key) => {
            const status = key.revoked_at ? 'Revoked' : key.redeemed_at ? 'Used' :
              new Date(key.expires_at).getTime() <= Date.now() ? 'Expired' : 'Active';
            return (
              <li key={key.enrolment_key_id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/10 p-3">
                <div>
                  <span className="font-mono text-sm text-slate-200">{key.key_prefix}…</span>
                  <p className="mt-1 text-xs text-slate-400">{status} · Expires {formatTime(key.expires_at)}</p>
                </div>
                {status === 'Active' && (
                  <RevokeControl label={`Revoke key ${key.key_prefix}`} disabled={busy} onConfirm={() => revoke(key.enrolment_key_id)} />
                )}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

const JOB_STATUS = {
  claimed: ['Claimed', 'text-cyan-200'],
  completed: ['Completed', 'text-emerald-300'],
  failed: ['Failed', 'text-red-300'],
  lease_expired: ['Lease expired', 'text-amber-200'],
  cancelled: ['Cancelled', 'text-slate-300'],
};

function JobsPanel({ token, invalidate }) {
  const jobs = useProviderCollection(fetchProviderJobs, token, invalidate);
  return (
    <section className={PANEL}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold">Recent jobs</h2>
          <p className="mt-1 text-sm text-slate-400">Up to 50 recent claims by machines on this account.</p>
        </div>
        <button className={BUTTON} type="button" onClick={jobs.refresh}>Refresh</button>
      </div>
      {jobs.error && <p className="mt-4 text-sm text-red-300" role="alert">{jobs.error}</p>}
      {!jobs.items && !jobs.error && <p className="mt-6 text-sm text-slate-400" role="status">Loading jobs…</p>}
      {jobs.items?.length === 0 && (
        <p className="mt-5 rounded-lg border border-dashed border-white/15 p-5 text-sm text-slate-300">No work has been claimed yet.</p>
      )}
      {!!jobs.items?.length && (
        <ul className="mt-5 divide-y divide-white/10 rounded-lg border border-white/10 bg-[#090d14]">
          {jobs.items.map((job) => {
            const [status, tone] = JOB_STATUS[job.status];
            return (
              <li key={`${job.workload}:${job.work_id}`} className="grid gap-3 p-4 sm:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
                <div className="min-w-0">
                  <h3 className="text-sm font-medium">{job.workload === 'inference' ? 'Model inference' : 'Blender frame'}</h3>
                  <p className="mt-1 wrap-anywhere font-mono text-xs text-slate-400">{job.work_id}</p>
                  <p className="mt-1 wrap-anywhere text-xs text-slate-400">Machine {job.node_id}</p>
                </div>
                <div className="min-w-0 text-xs text-slate-400 sm:text-right">
                  <p className={`text-sm font-medium ${tone}`}>{status}</p>
                  <p className="mt-1">Claimed {formatTime(job.claimed_at)}</p>
                  {job.completed_at && <p className="mt-1">Finished {formatTime(job.completed_at)}</p>}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function ProviderWorkspace({ session }) {
  const [tab, setTab] = useState('Machines');
  const { provider, token, invalidate } = session;

  return (
    <>
      <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-3xl font-semibold tracking-tight">Provider console</h1>
          <p className="mt-1 wrap-anywhere text-sm text-slate-400">{provider.display_name || provider.email}</p>
          <p className="mt-2 wrap-anywhere text-xs text-slate-400">
            Provider account ID <code className="text-slate-200">{provider.provider_account_id}</code>
          </p>
        </div>
        <button type="button" className={BUTTON} onClick={session.logout}><LogOut className="size-4" /> Sign out</button>
      </div>
      <nav aria-label="Provider console sections" className="mb-4 flex flex-wrap gap-2 border-b border-white/10 pb-4">
        {TABS.map(({ label, icon: Icon }) => (
          <button key={label} aria-pressed={tab === label} type="button" onClick={() => setTab(label)}
            className={BUTTON + (tab === label ? ' border-emerald-300/40 bg-emerald-300/10 text-emerald-100' : '')}>
            <Icon className="size-4" /> {label}
          </button>
        ))}
      </nav>
      {tab === 'Machines' && <MachinesPanel token={token} invalidate={invalidate} onEnrol={() => setTab('Enrolment keys')} />}
      {tab === 'Enrolment keys' && <EnrolmentPanel token={token} invalidate={invalidate} />}
      {tab === 'Jobs' && <JobsPanel token={token} invalidate={invalidate} />}
      {tab === 'Earnings' && (
        <section className={PANEL}>
          <h2 className="text-lg font-semibold">Earnings preview</h2>
          <p className="mt-2 text-sm text-slate-400">Earnings and payouts will become available after usage metering is enabled.</p>
        </section>
      )}
    </>
  );
}

export default function ProviderConsolePage({ route, onNavigate }) {
  const session = useProviderSession();
  const mode = route === '/provider/signup' ? 'signup' : 'login';

  return (
    <div className="min-h-screen bg-[#070a12] text-slate-100">
      <header className="border-b border-white/10">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <a href={import.meta.env.BASE_URL} className="inline-flex items-center gap-2 text-sm font-semibold"><Logo className="size-8" /> GPUOrbit</a>
          <a href="#/app" className="inline-flex items-center gap-2 text-sm text-slate-300 hover:text-white"><ArrowLeft className="size-4" /> Customer console</a>
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-4 py-7 sm:px-6 sm:py-12">
        {session.status === 'loading' && <p role="status" className="text-sm text-slate-300">Checking provider session…</p>}
        {session.status === 'error' && (
          <section className={PANEL} role="alert">
            <h1 className="text-lg font-semibold">Could not check your provider session</h1>
            <p className="mt-2 text-sm text-slate-300">{session.error}</p>
            <button type="button" className={BUTTON + ' mt-4'} onClick={session.refresh}>Retry</button>
          </section>
        )}
        {session.status === 'anonymous' && (
          <ProviderSignIn key={mode} mode={mode} authenticate={async (nextMode, fields) => {
            await session.authenticate(nextMode, fields);
            onNavigate('/provider');
          }} />
        )}
        {session.status === 'authenticated' && (
          <ProviderWorkspace key={session.provider.provider_account_id} session={{
            ...session,
            logout: () => {
              session.logout();
              onNavigate('/provider/login');
            },
          }} />
        )}
      </main>
    </div>
  );
}
