'use client';
import { useEffect, useState } from 'react';
import Shell from '@/components/Shell';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';

export default function Help() {
  const user = useAuth(['agent']);
  const [banner, setBanner] = useState(null);
  const [toast, setToast] = useState('');

  useEffect(() => {
    if (!user) return;
    api('/banner').then((d) => setBanner(d.incident)).catch(() => {});
  }, [user]);

  async function lockMe() {
    try {
      await api('/demo/lock-me', { method: 'POST' });
      setToast('Your demo AD account is now locked. Open a new chat and say you are locked out.');
    } catch (e) {
      setToast(e.message);
    }
    setTimeout(() => setToast(''), 4500);
  }

  if (!user) return null;
  return (
    <Shell user={user} active="/help">
      <div className="page-head">
        <div>
          <div className="eyebrow muted">Support</div>
          <h1>Help</h1>
        </div>
      </div>
      <div className="scroll">
        <div className="content">
          {banner && (
            <div className="card pad" style={{ marginBottom: 16, background: 'var(--amber-bg)', borderColor: 'var(--amber-line)' }}>
              <div className="eyebrow" style={{ color: '#8a6a1a' }}>Active incident</div>
              <h3 style={{ margin: '6px 0 4px' }}>{banner.title}</h3>
              <p style={{ color: '#6b4a00' }}>{banner.id} &middot; {banner.site} &middot; Next update {banner.next_update}. Sessions may be slow or freeze. Please do not file a separate ticket.</p>
            </div>
          )}
          <div className="help-grid">
            <div className="card pad">
              <h3>What Ridley can do</h3>
              <ul>
                <li>Unlock your account or reset your password after a one-time code.</li>
                <li>Raise an access request for a tool you need.</li>
                <li>Walk you through VPN, softphone, headset, WFH internet and Citrix fixes.</li>
                <li>Pass urgent or unusual problems to a technician with the whole chat attached.</li>
              </ul>
            </div>
            <div className="card pad">
              <h3>Keep it safe</h3>
              <ul>
                <li>Never type card numbers in chat. Ridley masks them, but do not send them.</li>
                <li>Ridley only acts on your own account.</li>
                <li>Lost or stolen device? Say so and Security is alerted at once.</li>
                <li>Phone support: local 4357 or the kiosk on your floor.</li>
              </ul>
            </div>
            <div className="card pad" style={{ gridColumn: '1 / -1' }}>
              <h3>Demo tools</h3>
              <p style={{ color: 'var(--muted)', margin: '0 0 12px' }}>For the capstone demo only. Locks your sample Active Directory account so you can try the unlock flow again.</p>
              <button className="btn" onClick={lockMe}>Lock my account</button>
            </div>
          </div>
        </div>
      </div>
      {toast && <div className="toast">{toast}</div>}
    </Shell>
  );
}
