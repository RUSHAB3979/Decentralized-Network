import React, { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, Check, Eye, EyeOff, LockKeyhole, Mail, User, Zap } from 'lucide-react';
import GithubMark from './icons/GithubMark';
import Logo from './Logo';
import GlowCursor from './fx/GlowCursor';
import { useSession } from '../hooks/useSession';
import Starfield from './fx/Starfield';
import FilmGrain from './fx/FilmGrain';
const benefits = [
    'One identity for render jobs, model APIs, and workstations',
    'Hard spending limits and auditable usage records',
    'Verified providers and isolated workload environments',
];
const baseUrl = import.meta.env.BASE_URL;
const AuthPage = ({ initialMode }) => {
    const [mode, setMode] = useState(initialMode);
    const [showPassword, setShowPassword] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const { status, user, signup, login } = useSession();
    const isSignup = mode === 'signup';

    // Somebody who is already signed in has no business on this page. Sending
    // them to the app rather than rendering a login form avoids the confusing
    // state where signing in "again" appears to do nothing.
    useEffect(() => {
        if (status === 'authenticated') window.location.hash = '/app/models';
    }, [status]);

    const switchMode = (next) => {
        setMode(next);
        setError('');
        window.location.hash = '/' + next;
    };

    const submit = async (event) => {
        event.preventDefault();
        // Read from the form rather than keeping a controlled input per field.
        // Fewer moving parts, and it keeps the password out of React state --
        // which matters because state ends up in devtools and in error reports.
        const data = new FormData(event.currentTarget);
        const email = String(data.get('email') ?? '');
        const password = String(data.get('password') ?? '');
        const displayName = String(data.get('name') ?? '');

        setBusy(true);
        setError('');
        try {
            if (isSignup) await signup({ email, password, displayName });
            else await login({ email, password });
            window.location.hash = '/app/models';
        }
        catch (err) {
            // The server's own wording, not a generic replacement. It already
            // distinguishes "that email already has an account" (409) from
            // "invalid email or password" (401) from a 503, and rewriting those
            // into one message would throw away the only useful part.
            setError(err.message || 'Something went wrong. Try again.');
        }
        finally {
            setBusy(false);
        }
    };
    return (<div className="relative min-h-[100svh] overflow-hidden bg-[#03040c] text-slate-100">
      <GlowCursor />
      <FilmGrain />
      <div className="pointer-events-none absolute inset-0 bg-grid-blueprint opacity-60"/>
      <Starfield className="pointer-events-none absolute inset-0 h-full w-full opacity-55" density={0.00012}/>
      <div className="pointer-events-none absolute -left-44 top-1/4 h-[34rem] w-[34rem] rounded-full bg-violet-500/[0.12] blur-[130px]"/>
      <div className="pointer-events-none absolute -right-40 bottom-0 h-[36rem] w-[36rem] rounded-full bg-cyan-400/[0.1] blur-[140px]"/>
      <div className="pointer-events-none absolute left-[42%] top-[-28%] h-[90%] w-[42%] rotate-[22deg] rounded-[50%] opacity-30 blur-3xl" style={{ background: 'linear-gradient(135deg, transparent 8%, rgba(129,140,248,.2), rgba(103,232,249,.1) 53%, transparent 76%)' }}/>

      <header className="relative z-20 mx-auto flex h-[82px] max-w-7xl items-center justify-between px-6 sm:px-10">
        <a href={baseUrl} className="flex items-center gap-3" data-mag>
          <Logo className="h-8 w-8"/>
          <span className="flex flex-col leading-none">
            <span className="text-[15px] font-semibold tracking-tight">NodeForge</span>
            <span className="mt-1 font-mono text-[9px] uppercase tracking-[0.32em] text-slate-500">GPU Fabric</span>
          </span>
        </a>
        <a href={baseUrl} className="group flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.16em] text-slate-400 transition-colors hover:text-white" data-mag>
          <ArrowLeft className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-1"/>
          Back to fabric
        </a>
      </header>

      <main className="relative z-10 mx-auto grid min-h-[calc(100svh-82px)] max-w-7xl items-center gap-14 px-6 pb-16 pt-8 lg:grid-cols-[1.05fr_.95fr] lg:px-10 lg:pb-24">
        <section className="hidden max-w-xl lg:block">
          <p className="eyebrow"><span className="eyebrow-accent"/>Secure access node</p>
          <h1 className="serif-display mt-8 text-[clamp(3.9rem,6vw,6.3rem)] leading-[0.94] text-slate-50">
            Your portal to<br />the <em className="serif-italic text-iridescent">liquid</em> cloud.
          </h1>
          <p className="mt-7 max-w-lg text-[16px] leading-7 text-slate-400">
            One identity for every GPU workflow. Enter the fabric and move from render jobs to model APIs without changing platforms.
          </p>
          <div className="mt-12 space-y-4">
            {benefits.map((benefit) => (<div key={benefit} className="flex items-center gap-4 text-sm text-slate-300">
                <span className="flex h-7 w-7 items-center justify-center rounded-full border border-cyan-300/20 bg-cyan-300/[0.06]">
                  <Check className="h-3.5 w-3.5 text-cyan-300"/>
                </span>
                {benefit}
              </div>))}
          </div>
          <div className="mt-14 flex items-center gap-5 border-t border-white/[0.07] pt-7">
            <div><p className="font-mono text-xl text-white">03</p><p className="mt-1 text-[9px] uppercase tracking-[0.25em] text-slate-600">Execution primitives</p></div>
            <div className="h-8 w-px bg-white/[0.08]"/>
            <div><p className="font-mono text-xl text-white">MVP</p><p className="mt-1 text-[9px] uppercase tracking-[0.25em] text-slate-600">Current stage</p></div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-[490px]">
          <div className="relative overflow-hidden rounded-[28px] border border-white/[0.1] bg-[#090b16]/75 p-6 shadow-[0_32px_100px_rgba(0,0,0,.55)] backdrop-blur-2xl sm:p-9">
            <div className="absolute inset-x-12 top-0 h-px bg-linear-to-r from-transparent via-cyan-300/70 to-transparent"/>
            <div className="absolute right-0 top-0 h-32 w-32 rounded-full bg-indigo-400/[0.08] blur-3xl"/>
            <div className="relative">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-[10px] uppercase tracking-[0.3em] text-cyan-300/70">Identity gateway / 01</p>
                  <h2 className="serif-display mt-3 text-4xl text-white">{isSignup ? 'Create your account' : 'Welcome back'}</h2>
                  <p className="mt-2 text-sm text-slate-500">{isSignup ? 'Join the world’s open GPU fabric.' : 'Reconnect to your NodeForge account.'}</p>
                </div>
                <span className="mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-indigo-300/15 bg-indigo-300/[0.06]">
                  <Zap className="h-5 w-5 text-indigo-300"/>
                </span>
              </div>

              <div className="mt-7 grid grid-cols-2 rounded-full border border-white/[0.08] bg-black/20 p-1">
                {['login', 'signup'].map((item) => (<button key={item} type="button" onClick={() => switchMode(item)} className={'rounded-full py-2.5 text-[11px] font-semibold uppercase tracking-[0.15em] transition-all ' + (mode === item ? 'bg-white/[0.09] text-white shadow-xs' : 'text-slate-500 hover:text-slate-300')}>
                    {item === 'login' ? 'Sign in' : 'Sign up'}
                  </button>))}
              </div>

              <div className="mt-6 grid grid-cols-2 gap-3">
                <button type="button" disabled title="Not available yet — use email" className="auth-social cursor-not-allowed opacity-40" data-mag><GithubMark className="h-4 w-4"/>GitHub</button>
                <button type="button" disabled title="Not available yet — use email" className="auth-social cursor-not-allowed opacity-40" data-mag><span className="text-base font-semibold text-iridescent">G</span>Google</button>
              </div>
              <div className="my-6 flex items-center gap-4">
                <span className="h-px flex-1 bg-white/[0.07]"/>
                <span className="font-mono text-[9px] uppercase tracking-[0.24em] text-slate-600">or continue with email</span>
                <span className="h-px flex-1 bg-white/[0.07]"/>
              </div>

              <form onSubmit={submit} className="space-y-4">
                {isSignup && (<label className="auth-field"><span>Display name</span><div><User className="h-4 w-4"/><input name="name" autoComplete="name" required placeholder="Your name"/></div></label>)}
                <label className="auth-field"><span>Email address</span><div><Mail className="h-4 w-4"/><input name="email" type="email" autoComplete="email" required placeholder="you@example.com"/></div></label>
                <label className="auth-field">
                  <span className="flex items-center justify-between">
                    Password
                    {!isSignup && <a href="#forgot" className="normal-case tracking-normal text-indigo-300 transition-colors hover:text-cyan-200">Forgot password?</a>}
                  </span>
                  <div>
                    <LockKeyhole className="h-4 w-4"/>
                    <input name="password" type={showPassword ? 'text' : 'password'} autoComplete={isSignup ? 'new-password' : 'current-password'} required minLength={isSignup ? 10 : 1} placeholder={isSignup ? 'At least 10 characters' : 'Enter your password'}/>
                    <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'} className="text-slate-500 transition-colors hover:text-white">
                      {showPassword ? <EyeOff className="h-4 w-4"/> : <Eye className="h-4 w-4"/>}
                    </button>
                  </div>
                </label>
                {isSignup && (<label className="flex items-start gap-3 pt-1 text-xs leading-5 text-slate-500">
                    <input type="checkbox" required className="mt-1 accent-indigo-400"/>
                    <span>I agree to the <a href="#terms" className="text-slate-300 hover:text-white">Terms</a> and <a href="#privacy" className="text-slate-300 hover:text-white">Privacy Policy</a>.</span>
                  </label>)}
                <button type="submit" disabled={busy} className="btn-liquid group mt-2 !flex w-full justify-center !py-3.5 disabled:cursor-not-allowed disabled:opacity-60" data-mag>
                  {busy
                    ? (isSignup ? 'Creating account…' : 'Signing in…')
                    : (isSignup ? 'Create account' : 'Enter the fabric')}
                  {!busy && <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1"/>}
                </button>
                {error && (<p role="alert" className="rounded-xl border border-rose-400/25 bg-rose-500/[0.07] px-4 py-3 text-center text-xs text-rose-200">{error}</p>)}
              </form>

              <p className="mt-6 text-center text-xs text-slate-500">
                {isSignup ? 'Already forged an identity?' : 'New to the fabric?'}{' '}
                <button type="button" onClick={() => switchMode(isSignup ? 'login' : 'signup')} className="font-medium text-indigo-300 transition-colors hover:text-cyan-200">
                  {isSignup ? 'Sign in' : 'Create an account'}
                </button>
              </p>
            </div>
          </div>
          <div className="mt-5 flex items-center justify-center gap-2 font-mono text-[9px] uppercase tracking-[0.24em] text-slate-600">
            <span className={'h-1.5 w-1.5 rounded-full ' + (status === 'error' ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,.8)]' : 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,.8)]')}/>
            {status === 'error' ? 'Orchestrator unreachable' : 'Connected to orchestrator'}
          </div>
        </section>
      </main>
    </div>);
};
export default AuthPage;
