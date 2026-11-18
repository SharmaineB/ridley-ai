'use client';
import { useEffect, useState } from 'react';
import Shell from '@/components/Shell';
import Icon from '@/components/Icons';
import { api, download } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';
import { dateTime } from '@/lib/format';

const ACCOUNTS = ['All accounts', 'PayNova', 'ShopLoop', 'ClearFeed'];
const STATUS = ['All', 'Open', 'In Progress', 'Escalated', 'Resolved', 'Redirected'];
const PRIO = ['All', 'P1', 'P2', 'P3', 'P4'];

export default function AllTickets() {
  const user = useAuth(['technician', 'admin']);
  const [q, setQ] = useState('');
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState('All');
  const [prio, setPrio] = useState('All');
  const [account, setAccount] = useState('All accounts');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => { setQuery(q); setPage(1); }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const params = `q=${encodeURIComponent(query)}&status=${encodeURIComponent(status)}&priority=${prio}&account=${encodeURIComponent(account)}`;

  useEffect(() => {
    if (!user) return;
    api(`/admin/tickets?${params}&page=${page}&page_size=10`).then(setData).catch(() => {});
  }, [user, params, page]);

  if (!user) return null;
  const s = data?.stats;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const from = data && data.total ? (page - 1) * data.page_size + 1 : 0;
  const to = data ? Math.min(page * data.page_size, data.total) : 0;

  return (
    <Shell user={user} active="/all-tickets">
      <div className="page-head">
        <div>
          <div className="eyebrow muted">All employees</div>
          <h1>All tickets</h1>
        </div>
        <div className="dash-right">
          <div className="seg">{ACCOUNTS.map((a) => <button key={a} className={account === a ? 'on' : ''} onClick={() => { setAccount(a); setPage(1); }}>{a}</button>)}</div>
          <button className="btn primary" onClick={() => download(`/admin/tickets?${params}&export=true`, 'tickets.csv')}><Icon name="download" size={16} />Export CSV</button>
        </div>
      </div>
      <div className="scroll">
        <div className="content">
          <div className="stats">
            <div className="card stat"><div className="label">Tickets</div><div className="value">{s?.tickets ?? '-'}</div><div className="sub">From {s?.employees ?? '-'} employees</div></div>
            <div className="card stat"><div className="label">Open now</div><div className="value">{s?.open_now ?? '-'}</div><div className="sub">Open, in progress or escalated</div></div>
            <div className="card stat"><div className="label">Resolved by Ridley</div><div className="value green">{s?.resolved_by_ridley ?? '-'}</div><div className="sub">{s?.ridley_pct ?? 0}% of all tickets</div></div>
            <div className="card stat"><div className="label">SLA breached</div><div className="value red">{s?.sla_breached ?? '-'}</div><div className="sub">Open past the KB-014 target</div></div>
          </div>
          <div className="card table-card">
            <div className="toolbar">
              <div style={{ display: 'flex', gap: 14, alignItems: 'center' }}>
                <div className="searchbox"><Icon name="search" size={17} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search ticket ID, employee name or ID, summary" /></div>
                <span style={{ color: 'var(--muted)', fontSize: 13, whiteSpace: 'nowrap' }}>{data ? `${data.total} ticket${data.total === 1 ? '' : 's'}` : ''}</span>
              </div>
              <div className="pill-row">
                <span className="pill-label">Status</span>
                {STATUS.map((x) => <button key={x} className={`pill ${status === x ? 'on' : ''}`} onClick={() => { setStatus(x); setPage(1); }}>{x}</button>)}
                <span className="pill-label" style={{ marginLeft: 12 }}>Priority</span>
                {PRIO.map((x) => <button key={x} className={`pill ${prio === x ? 'on' : ''}`} onClick={() => { setPrio(x); setPage(1); }}>{x}</button>)}
              </div>
            </div>
            {data && data.tickets.length === 0 ? (
              <div className="empty"><b>No tickets found</b>Change the search or filters.</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="t">
                  <thead><tr><th>Ticket</th><th>Employee</th><th>Summary</th><th>Priority</th><th>Assigned group</th><th>Status</th><th>Created</th><th>Resolution / SLA</th></tr></thead>
                  <tbody>
                    {(data?.tickets || []).map((t) => (
                      <tr key={t.ticket_id}>
                        <td className="id">{t.ticket_id}</td>
                        <td><b>{t.employee_name}</b><small>{t.employee_id} &middot; {t.account}</small></td>
                        <td><b>{t.summary}</b><small>{t.category}</small></td>
                        <td><span className={`prio ${t.priority}`}>{t.priority}</span></td>
                        <td>{t.assigned_group}</td>
                        <td><span className={`status ${t.status.replace(' ', '')}`}>{t.status}</span></td>
                        <td style={{ whiteSpace: 'nowrap' }}>{dateTime(t.created_at)}</td>
                        <td style={{ fontWeight: 650, whiteSpace: 'nowrap', color: t.breached ? 'var(--red)' : 'inherit' }}>{t.breached ? 'SLA breached' : t.sla}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            <div className="pager">
              <span>Showing {from}&ndash;{to} of {data?.total ?? 0} &middot; Page {page} of {pages}</span>
              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn small" disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</button>
                <button className="btn small" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</button>
              </div>
            </div>
          </div>
          <p className="foot-note">SLA targets from KB-014: P1 4 h, P2 8 h, P3 2 business days, P4 5 business days. All records are synthetic sample data.</p>
        </div>
      </div>
    </Shell>
  );
}
