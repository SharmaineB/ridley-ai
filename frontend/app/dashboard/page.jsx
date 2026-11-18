'use client';
import { useEffect, useState } from 'react';
import Shell from '@/components/Shell';
import Icon from '@/components/Icons';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';
import { rangeLabel } from '@/lib/format';

const ACCOUNTS = ['All accounts', 'PayNova', 'ShopLoop', 'ClearFeed'];
const RANGES = [{ label: 'All time', days: '' }, { label: 'Last 90 days', days: 90 }, { label: 'Last 30 days', days: 30 }];

function LineChart({ data }) {
  const W = 640;
  const H = 230;
  const pad = { l: 36, r: 12, t: 12, b: 28 };
  if (!data.length) return <div className="empty">No data for this range</div>;
  const max = Math.max(10, ...data.map((d) => Math.max(d.ai, d.escalated)));
  const top = Math.ceil(max / 10) * 10;
  const x = (i) => pad.l + (i * (W - pad.l - pad.r)) / Math.max(1, data.length - 1);
  const y = (v) => pad.t + (1 - v / top) * (H - pad.t - pad.b);
  const path = (key) => data.map((d, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(d[key]).toFixed(1)}`).join(' ');
  const ticks = [0, top / 3, (2 * top) / 3, top].map((v) => Math.round(v));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" role="img" aria-label="AI resolved versus escalated tickets per week">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="#e7eded" />
          <text x={pad.l - 8} y={y(t) + 4} textAnchor="end" fontSize="11" fill="#8a9a9b">{t}</text>
        </g>
      ))}
      <path d={path('ai')} fill="none" stroke="#0f5257" strokeWidth="2.2" strokeLinejoin="round" />
      <path d={path('escalated')} fill="none" stroke="#b7791f" strokeWidth="2.2" strokeLinejoin="round" />
      {data.map((d, i) => (i % Math.ceil(data.length / 6) === 0 && (i + 3 < data.length || i === data.length - 1) ? <text key={d.week} x={x(i)} y={H - 6} textAnchor={i === data.length - 1 ? 'end' : i === 0 ? 'start' : 'middle'} fontSize="11" fill="#8a9a9b">{d.week}</text> : null))}
    </svg>
  );
}

export default function Dashboard() {
  const user = useAuth(['admin']);
  const [account, setAccount] = useState('All accounts');
  const [days, setDays] = useState('');
  const [m, setM] = useState(null);

  useEffect(() => {
    if (!user) return;
    api(`/admin/metrics?account=${encodeURIComponent(account)}${days ? `&days=${days}` : ''}`).then(setM).catch(() => {});
  }, [user, account, days]);

  if (!user) return null;
  const maxCat = m ? Math.max(1, ...m.categories.map((c) => c.count)) : 1;

  return (
    <Shell user={user} active="/dashboard">
      <div className="dash-head">
        <div>
          <div className="eyebrow muted">Ridley performance</div>
          <h1>Support overview</h1>
        </div>
        <div className="dash-right">
          <label className="range-chip">
            <Icon name="calendar" size={16} />
            <select value={days} onChange={(e) => setDays(e.target.value)} style={{ border: 0, background: 'transparent', fontWeight: 550, outline: 0 }}>
              {RANGES.map((r) => <option key={r.label} value={r.days}>{r.label}</option>)}
            </select>
          </label>
          <div className="seg">
            {ACCOUNTS.map((a) => <button key={a} className={account === a ? 'on' : ''} onClick={() => setAccount(a)}>{a}</button>)}
          </div>
        </div>
      </div>
      <div className="scroll">
        <div className="content">
          {!m ? <div className="empty">Loading metrics...</div> : (
            <>
              <div className="stats">
                <div className="card stat">
                  <div className="label">Deflection rate</div>
                  <div className="value">{m.deflection_rate}%</div>
                  <div className="sub">{m.ai_resolved} of {m.total} tickets resolved without a technician</div>
                </div>
                <div className="card stat">
                  <div className="label">Mean time to resolution</div>
                  <div className="value">{m.mttr_hours} h</div>
                  <div className="sub">Average across resolved tickets, AI and human</div>
                </div>
                <div className="card stat">
                  <div className="label">p95 response time <span className="tag">Measured</span></div>
                  <div className="value">{m.p95_latency_s} s</div>
                  <div className="sub">From {m.latency_samples} replies. Target under 5 s at 20 concurrent users.</div>
                </div>
                <div className="card stat">
                  <div className="label">CSAT</div>
                  <div className="value">{m.csat} <small>/ 5</small></div>
                  <div className="sub">Average rating on {m.csat_count} rated chats</div>
                </div>
              </div>
              <div className="grid-2">
                <div className="card pad">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div className="chart-title">AI-resolved vs escalated per week</div>
                      <div className="chart-sub">Full weeks, {rangeLabel(m.range)}</div>
                    </div>
                    <div className="legend"><span><i style={{ background: '#0f5257' }} />AI-resolved</span><span><i style={{ background: '#b7791f' }} />Escalated</span></div>
                  </div>
                  <div style={{ marginTop: 10 }}><LineChart data={m.weekly} /></div>
                </div>
                <div className="card pad">
                  <div className="chart-title">Tickets by category</div>
                  <div className="chart-sub" style={{ marginBottom: 18 }}>Top {m.categories.length} of {m.total} tickets</div>
                  {m.categories.map((c) => (
                    <div className="catrow" key={c.name}>
                      <div className="nm"><span>{c.name}</span><b>{c.count}</b></div>
                      <div className="bar"><i style={{ width: `${(c.count / maxCat) * 100}%` }} /></div>
                    </div>
                  ))}
                </div>
              </div>
              <div className="card table-card">
                <div style={{ padding: '18px 22px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div><div className="chart-title">Top intents, last 14 days</div><div className="chart-sub">What agents asked Ridley for most</div></div>
                  <a href="/audit" style={{ color: 'var(--teal)', fontWeight: 600, fontSize: 13 }}>Open audit log &rarr;</a>
                </div>
                <table className="t">
                  <thead><tr><th>Intent</th><th>Example</th><th>KB article</th><th>Route</th><th style={{ textAlign: 'right' }}>Tickets</th></tr></thead>
                  <tbody>
                    {m.top_intents.map((r) => (
                      <tr key={r.intent}>
                        <td className="mono" style={{ fontSize: 12.5 }}>{r.intent}</td>
                        <td>{r.example}</td>
                        <td style={{ color: 'var(--teal)', fontWeight: 600 }}>{r.kb}</td>
                        <td><span className={`route ${r.route}`}>{r.route}</span></td>
                        <td style={{ textAlign: 'right', fontWeight: 650 }}>{r.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </Shell>
  );
}
