'use client';
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Icon, { LogoMark } from '@/components/Icons';
import { api, getToken, getUser, homeFor, saveSession } from '@/lib/api';

const DEMO = [
  { id: 'NX-20004', label: 'Agent' },
  { id: 'NX-30001', label: 'Technician' },
  { id: 'NX-90001', label: 'Admin' },
];

export default function Login() {
  const router = useRouter();
  const [employeeId, setEmployeeId] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const u = getUser();
    if (getToken() && u) router.replace(homeFor(u.role));
  }, []);

  async function submit(e) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const d = await api('/auth/login', { method: 'POST', body: { employee_id: employeeId, password } });
      saveSession(d.token, d.user);
      router.replace(homeFor(d.user.role));
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <section className="login-left">
        <div className="brand">
          <LogoMark size={48} />
          <b>Ridley <span>AI</span></b>
        </div>
        <div className="mid">
          <div className="rule" />
          <div className="eyebrow">Your IT support assistant</div>
          <h1>Fix IT issues<br />in minutes, not queues.</h1>
          <p>Fast, trusted answers that keep every conversation moving.</p>
        </div>
        <div className="foot">
          <span>Built for TaskUs teams</span>
          <span><i />Secure internal access</span>
        </div>
      </section>
      <section className="login-right">
        <form className="login-form" onSubmit={submit}>
          <div className="eyebrow">Welcome back</div>
          <h2>Sign in to Ridley</h2>
          <p className="sub">Use your TaskUs employee credentials to continue.</p>
          {error && (
            <div className="alert err" role="alert">
              <Icon name="alert" size={20} />
              <div><b>Unable to sign in</b>{error}</div>
            </div>
          )}
          <div className="field">
            <label htmlFor="eid">Employee ID</label>
            <input id="eid" className={`input ${error ? 'err' : ''}`} value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} placeholder="NX-20004" autoComplete="username" required />
          </div>
          <div className="field">
            <label htmlFor="pw">Password</label>
            <div className="input-wrap">
              <input id="pw" className={`input ${error ? 'err' : ''}`} type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" required />
              <button type="button" onClick={() => setShow(!show)} aria-label="Show password"><Icon name={show ? 'eyeoff' : 'eye'} /></button>
            </div>
          </div>
          <button className="btn primary signin" disabled={busy}>
            <span style={{ flex: 1, textAlign: 'center' }}>{busy ? 'Signing in...' : 'Sign in'}</span>
            <Icon name="arrow" />
          </button>
          <div className="hint">
            <Icon name="info" size={18} />
            <span><b>Locked out?</b> Use the kiosk or call local 4357.</span>
          </div>
          <div className="demo-box">
            Demo accounts (password ridley2026):<br />
            {DEMO.map((d) => (
              <button key={d.id} type="button" onClick={() => { setEmployeeId(d.id); setPassword('ridley2026'); }}>{d.label} {d.id}</button>
            ))}
          </div>
          <p className="legal">Authorized TaskUs users only. Activity may be monitored for security.</p>
        </form>
      </section>
    </div>
  );
}
