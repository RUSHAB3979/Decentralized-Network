import React, { useEffect, useState } from 'react';
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail, Zap } from 'lucide-react';
import Logo from './Logo';
import GlowCursor from './fx/GlowCursor';
import { useSession } from '../hooks/useSession';
import Starfield from './fx/Starfield';
import FilmGrain from './fx/FilmGrain';
const baseUrl = import.meta.env.BASE_URL;
const AuthPage = () => {
    const [showPassword, setShowPassword] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const { status, login } = useSession();

    // Somebody who is already signed in has no business on this page. Sending
    // them to the app rather than rendering a login form avoids the confusing
    // state where signing in "again" appears to do nothing.
    useEffect(() => {
        if (status === 'authenticated') window.location.hash = '/app/models';
    }, [status]);

    const submit = async (event) => {
        event.preventDefault();
        // Read from the form rather than keeping a controlled input per field.
        // Fewer moving parts, and it keeps the password out of React state --
        // which matters because state ends up in devtools and in error reports.
        const data = new FormData(event.currentTarget);
        const email = String(data.get('email') ?? '');
        const password = String(data.get('password') ?? '');

        setBusy(true);
        setError('');
        try {
            await login({ email, password });
            window.location.hash = '/app/models';
        }
        catch (err) {
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
            <span className="text-[15px] font-semibold tracking-tight">GPUOrbit</span>
            <span className="mt-1 font-mono text-[9px] uppercase tracking-[0.32em] text-slate-500">P2P Compute</span>
          </span>
        </a>
        <a href={baseUrl} className="group flex items-center gap-2 text-[12px] font-medium uppercase tracking-[0.16em] text-slate-400 transition-colors hover:text-white" data-mag>
          <ArrowLeft className="h-3.5 w-3.5 transition-transform group-hover:-translate-x-1"/>
          Back to home
        </a>
      </header>

      <main className="relative z-10 mx-auto grid min-h-[calc(100svh-82px)] max-w-7xl items-center gap-14 px-6 pb-16 pt-8 lg:grid-cols-[1.05fr_.95fr] lg:px-10 lg:pb-24">
        <section className="hidden max-w-xl lg:block">
          <p className="serif-display text-[clamp(3.9rem,6vw,6.3rem)] leading-[0.94] text-slate-50">
            GPUOrbit <em className="serif-italic text-iridescent">inference pilot</em>
          </p>
          <p className="mt-7 max-w-lg text-[16px] leading-7 text-slate-400">
            Create an API key, find the available model and send a test request with synthetic data.
          </p>
        </section>

        <section className="mx-auto w-full max-w-[490px]">
          <div className="relative overflow-hidden rounded-[28px] border border-white/[0.1] bg-[#090b16]/75 p-6 shadow-[0_32px_100px_rgba(0,0,0,.55)] backdrop-blur-2xl sm:p-9">
            <div className="absolute inset-x-12 top-0 h-px bg-linear-to-r from-transparent via-cyan-300/70 to-transparent"/>
            <div className="absolute right-0 top-0 h-32 w-32 rounded-full bg-indigo-400/[0.08] blur-3xl"/>
            <div className="relative">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h1 className="serif-display text-4xl text-white">Customer sign-in</h1>
                  <p className="mt-2 text-sm text-slate-400">Customer access is by invitation. Use the account provided by your pilot administrator.</p>
                </div>
                <span className="mt-1 flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-indigo-300/15 bg-indigo-300/[0.06]">
                  <Zap className="h-5 w-5 text-indigo-300"/>
                </span>
              </div>

              <form onSubmit={submit} className="mt-7 space-y-4">
                <label className="auth-field"><span>Email address</span><div><Mail className="h-4 w-4"/><input name="email" type="email" autoComplete="username" required placeholder="you@example.com"/></div></label>
                <label className="auth-field">
                  <span>Password</span>
                  <div>
                    <LockKeyhole className="h-4 w-4"/>
                    <input name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required placeholder="Enter your password"/>
                    <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'} className="text-slate-500 transition-colors hover:text-white">
                      {showPassword ? <EyeOff className="h-4 w-4"/> : <Eye className="h-4 w-4"/>}
                    </button>
                  </div>
                </label>
                <button type="submit" disabled={busy} className="btn-liquid group mt-2 !flex w-full justify-center !py-3.5 disabled:cursor-not-allowed disabled:opacity-60" data-mag>
                  {busy ? 'Signing in…' : 'Sign in'}
                  {!busy && <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1"/>}
                </button>
                {error && (<p role="alert" className="rounded-xl border border-rose-400/25 bg-rose-500/[0.07] px-4 py-3 text-center text-xs text-rose-200">{error}</p>)}
              </form>

              <p className="mt-6 text-center text-xs text-slate-400">Need a password reset? Contact your pilot administrator.</p>
            </div>
          </div>
        </section>
      </main>
    </div>);
};
export default AuthPage;
