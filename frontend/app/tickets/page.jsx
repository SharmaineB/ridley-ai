'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import Shell from '@/components/Shell';
import Icon from '@/components/Icons';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';
import { dateTime } from '@/lib/format';

const STATUS = ['All', 'Open', 'In Progress', 'Resolved'];
const PRIO = ['All', 'P1', 'P2', 'P3', 'P4'];

export default function MyTickets() {
  const user = useAuth(['agent']);
  const [status, setStatus] = useState('All');
  const [prio, setPrio] = useState('All');
  const [data, setData] = useState(null);
  const [banner, setBanner] = useState(null);

  useEffect(() => {
    if (!user) return;
    api('/banner').then((d) => setBanner(d.incident)).catch(() => {});
  }, [user]);

  useEffect(() => {
    if (!user) return;
    api(`/tickets?status=${encodeURIComponent(status)}&priority=${prio}`).then(setData).catch(() => {});
  }, [user, status, prio]);

  if (!user) return null;
  const c = data?.counts;

  return (
    <Shell user={user} active="/tickets">
      <div className="page-head">
        <div>
          <div className="eyebrow muted">Support history</div>
          <h1>My tickets</h1>
        </div>
        <Link href="/chat" className="btn primary"><Icon name="plus" size={16} />Get help in chat</Link>
      </div>
      {banner && (
        <div className="banner">
          <span className="dot">!</span>
          <div><b>{banner.title}</b><small>{banner.id} &middot; Next update {banner.next_update} &middot; No need to file a separate ticket</small></div>
          <Link href="/help">View incident &rarr;</Link>
        </div>
      )}
      <div className="scroll">
        <div className="content">
          <div className="stats">
            <div className="card stat"><div className="label">Open</div><div className="value">{c?.open ?? '-'}</div></div>
            <div className="card stat"><div className="label">In progress</div><div className="value">{c?.in_progress ?? '-'}</div></div>
            <div className="card stat">
              <div className="label">Resolved by Ridley</div>
              <div className="value green">{c?.resolved_by_ridley ?? '-'}</div>
              <div className="sub">{c ? `${c.resolved_by_ridley} of ${c.resolved_total} resolved tickets` : ''}</div>
            </div>
            <div className="card stat">
              <div className="label">All my tickets</div>
              <div className="value">{c?.all ?? '-'}</div>
              <div className="sub">{c ? `Since ${c.since}` : ''}</div>
            </div>
          </div>
          <div className="card table-card">
            <div className="toolbar">
              <div className="pill-row">
                <span className="pill-label">Status</span>
                {STATUS.map((s) => <button key={s} className={`pill ${status === s ? 'on' : ''}`} onClick={() => setStatus(s)}>{s}</button>)}
                <span className="pill-label" style={{ marginLeft: 12 }}>Priority</span>
                {PRIO.map((p) => <button key={p} className={`pill ${prio === p ? 'on' : ''}`} onClick={() => setPrio(p)}>{p}</button>)}
                <span style={{ marginLeft: 'auto', color: 'var(--muted)', fontSize: 13 }}>{data ? `${data.tickets.length} ticket${data.tickets.length === 1 ? '' : 's'}` : ''}</span>
              </div>
            </div>
            {data && data.tickets.length === 0 ? (
              <div className="empty"><b>No tickets match these filters</b>Try a different status or priority, or start a chat if something is broken.</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="t">
                  <thead>
                    <tr><th>Ticket ID</th><th>Summary</th><th>Category</th><th>Priority</th><th>Assigned group</th><th>Status</th><th>Created</th><th>SLA remaining</th></tr>
                  </thead>
                  <tbody>
                    {(data?.tickets || []).map((t) => (
                      <tr key={t.ticket_id}>
                        <td className="id">{t.ticket_id}</td>
                        <td style={{ fontWeight: 600, maxWidth: 220 }}>{t.summary}</td>
                        <td>{t.category}</td>
                        <td><span className={`prio ${t.priority}`}>{t.priority}</span></td>
                        <td>{t.assigned_group}</td>
                        <td><span className={`status ${t.status.replace(' ', '')}`}>{t.status}</span></td>
                        <td style={{ whiteSpace: 'nowrap' }}>{dateTime(t.created_at)}</td>
                        <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{t.sla}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
          <p className="foot-note">Showing your tickets only. The server returns only tickets for {user.employee_id}.</p>
        </div>
      </div>
    </Shell>
  );
}
