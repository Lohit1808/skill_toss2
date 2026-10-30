import { useState, type FormEvent } from 'react';
import { AlertCircle, CheckCircle2, Loader2, Lock } from 'lucide-react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { clearStoredSession, completePassword } from '@/lib/djangoApi';

export function PasswordLinkPage({ kind }: { kind: 'set' | 'reset' }) {
  const navigate = useNavigate();
  const [search] = useSearchParams();
  const uid = search.get('uid') ?? '';
  const token = search.get('token') ?? '';
  const [password, setPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const validLinkShape = Boolean(token && (kind === 'set' || uid));
  const title = kind === 'set' ? 'Set up your password' : 'Reset your password';

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (password !== confirmation) {
      setError('The password confirmation does not match.');
      return;
    }
    try {
      setSubmitting(true);
      await completePassword(kind, uid, token, password, confirmation);
      clearStoredSession();
      navigate(`/login?password=${kind}`, { replace: true });
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'This password link could not be used.');
    } finally {
      setSubmitting(false);
    }
  };

  return <main className="flex min-h-screen items-center justify-center bg-ink-50 p-4">
    <div className="w-full max-w-md rounded-dialog border border-ink-200 bg-white p-6 shadow-card sm:p-8">
      <div className="mb-5 flex h-11 w-11 items-center justify-center rounded-card bg-primary-50 text-primary-700"><Lock className="h-5 w-5" /></div>
      <h1 className="font-display text-2xl font-bold text-ink-950">{title}</h1>
      <p className="mt-2 text-sm leading-6 text-ink-600">Choose a private password. The link is time-limited and can only be used once.</p>
      {!validLinkShape ? <div role="alert" className="mt-5 rounded-control border border-error-200 bg-error-50 p-3 text-sm text-error-700"><AlertCircle className="mr-2 inline h-4 w-4" />This password link is incomplete. Request a new link or contact your administrator.</div> : <form onSubmit={submit} className="mt-5 space-y-4">
        {error && <div role="alert" className="rounded-control border border-error-200 bg-error-50 p-3 text-sm text-error-700"><AlertCircle className="mr-2 inline h-4 w-4" />{error}</div>}
        <div><label className="label" htmlFor="link-new-password">New password</label><input id="link-new-password" type="password" autoComplete="new-password" minLength={8} required disabled={submitting} value={password} onChange={(event) => setPassword(event.target.value)} className="input" /></div>
        <div><label className="label" htmlFor="link-confirm-password">Confirm new password</label><input id="link-confirm-password" type="password" autoComplete="new-password" minLength={8} required disabled={submitting} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} className="input" /></div>
        <button type="submit" disabled={submitting} className="btn-primary w-full justify-center">{submitting ? <><Loader2 className="h-4 w-4 animate-spin" /> Updating password…</> : <><CheckCircle2 className="h-4 w-4" /> {title}</>}</button>
      </form>}
      <Link to="/login" className="focus-ring mt-5 inline-block rounded text-sm font-medium text-primary-700">Return to sign in</Link>
    </div>
  </main>;
}
