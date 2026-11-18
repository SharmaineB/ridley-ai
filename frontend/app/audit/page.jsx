'use client';
import { useEffect, useState } from 'react';
import Shell from '@/components/Shell';
import Icon from '@/components/Icons';
import { api, download } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';
import { dateTime } from '@/lib/format';

const GCLASS = { 'PII redacted': 'pii', 'Injection blocked': 'inj', 'RBAC denied': 'rbac' };

export default function Audit() {
  const user = useAuth(['admin']);
  const [tab, setTab] = useState('guardrail');
  const [type, setType] = useState('All');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);

  const params = `tab=${tab}&type=${encodeURIComponent(type)}${start ? `&start=${start}` : ''}${end ? `&end=${end}` : ''}`;

  useEffect(() => {
    if (!user) return;
    api(`/audit?${params}&page=${page}&page_size=12`).then(setData).catch(() => {});
  }, [user, params, page]);

  if (!user) return null;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;
  const from = data && data.total ? (page - 1) * data.page_size + 1 : 0;
  const to = data ? Math.min(page * data.page_size, data.total) : 0;

  function switchTab(t) {
    setTab(t);
    setType('All');
    setPage(1);
  }

  return (
    <Shell user={user} active="/audit">
      <div className="page-head">
        <div>
          <div className="eyebrow muted">Compliance</div>
          <h1>Audit log</h1>
        </div>
        <div className="dash-right">
          <button className="btn primary" onClick={() => download(`/audit?${params}&export=true`, `audit-${tab}.csv`)}><Icon name="download" size={16} />Export CSV</button>
        </div>
      </div>
      <div className="scroll">
        <div className="content">
          <div className="card table-card">
            <div className="tabs">
              <button className={tab === 'guardrail' ? 'on' : ''} onClick={() => switchTab('guardrail')}>Guardrail events<em>{data?.counts.guardrail ?? 0}</em></button>
              <button className={tab === 'function' ? 'on' : ''} onClick={() => switchTab('function')}>Function calls<em>{data?.counts.function ?? 0}</em></button>
            </div>
            <div className="filters">
              <select className="select" value={type} onChange={(e) => { setType(e.target.value); setPage(1); }} aria-label="Type">
                <option value="All">{tab === 'guardrail' ? 'All event types' : 'All functions'}</option>
                {(data?.types || []).map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--muted)' }}>From
                <input type="date" className="select" value={start} onChange={(e) => { setStart(e.target.value); setPage(1); }} />
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--muted)' }}>To
                <input type="date" className="select" value={end} onChange={(e) => { setEnd(e.target.value); setPage(1); }} />
              </label>
              {(start || end || type !== 'All') && <button className="btn small" onClick={() => { setStart(''); setEnd(''); setType('All'); setPage(1); }}>Clear</button>}
            </div>
            {data && data.items.length === 0 ? (
              <div className="empty"><b>No records</b>Change the filters.</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                {tab === 'guardrail' ? (
                  <table className="t">
                    <thead><tr><th>Time</th><th>Employee</th><th>Type</th><th>Action</th><th>Detail</th></tr></thead>
                    <tbody>
                      {(data?.items || []).map((r, i) => (
                        <tr key={i}>
                          <td style={{ whiteSpace: 'nowrap' }}>{dateTime(r.time)}</td>
                          <td><b>{r.employee}</b><small>{r.employee_id}</small></td>
                          <td><span className={`gtype ${GCLASS[r.type] || ''}`}>{r.type}</span></td>
                          <td>{r.action}</td>
                          <td style={{ color: '#3c5052' }}>{r.detail}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <table className="t">
                    <thead><tr><th>Time</th><th>Employee</th><th>Function</th><th>Arguments</th><th>Result</th></tr></thead>
                    <tbody>
                      {(data?.items || []).map((r, i) => (
                        <tr key={i}>
                          <td style={{ whiteSpace: 'nowrap' }}>{dateTime(r.time)}</td>
                          <td><b>{r.employee}</b><small>{r.employee_id}</small></td>
                          <td className="mono" style={{ fontSize: 12.5 }}>{r.function}</td>
                          <td className="mono" style={{ fontSize: 12, color: '#3c5052' }}>{r.arguments}</td>
                          <td>{r.result}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
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
          <p className="foot-note">Employee messages are stored only after redaction. Raw card numbers, passwords and IDs never reach the database.</p>
        </div>
      </div>
    </Shell>
  );
}
