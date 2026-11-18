'use client';
import { useCallback, useEffect, useState } from 'react';
import Shell from '@/components/Shell';
import Icon from '@/components/Icons';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';
import { dateTime } from '@/lib/format';

const EMPTY = { kb_id: '', title: '', category: '', body: '' };

export default function KnowledgeBase() {
  const user = useAuth(['technician', 'admin']);
  const [data, setData] = useState(null);
  const [q, setQ] = useState('');
  const [cat, setCat] = useState('All');
  const [status, setStatus] = useState('All');
  const [query, setQuery] = useState('');
  const [result, setResult] = useState(null);
  const [testing, setTesting] = useState(false);
  const [modal, setModal] = useState(false);
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState('');

  const load = useCallback(() => api('/kb/articles').then(setData).catch(() => {}), []);
  useEffect(() => { if (user) load(); }, [user, load]);

  function say(t) {
    setToast(t);
    setTimeout(() => setToast(''), 3500);
  }

  async function runTest(e) {
    e.preventDefault();
    if (!query.trim()) return;
    setTesting(true);
    try {
      setResult(await api('/kb/test-retrieval', { method: 'POST', body: { query } }));
    } finally {
      setTesting(false);
    }
  }

  async function reindex() {
    setBusy(true);
    try {
      const d = await api('/kb/reindex', { method: 'POST' });
      say(`Re-indexed ${d.chunks} chunks`);
      load();
    } finally {
      setBusy(false);
    }
  }

  async function upload(e) {
    e.preventDefault();
    setError('');
    if (!form.kb_id.trim() || !form.title.trim() || !form.category.trim() || !form.body.trim()) {
      setError('Fill in every field.');
      return;
    }
    setBusy(true);
    try {
      const d = await api('/kb/articles', { method: 'POST', body: form });
      setModal(false);
      setForm(EMPTY);
      say(`${d.article.kb_id} saved as ${d.article.version}. ${d.chunks} chunks indexed`);
      load();
    } catch (err) {
      setError(err.message || 'Upload failed');
    } finally {
      setBusy(false);
    }
  }

  if (!user) return null;
  const rows = data?.articles || [];
  const cats = ['All', ...Array.from(new Set(rows.map((r) => r.category))).sort()];
  const shown = rows.filter((r) =>
    (cat === 'All' || r.category === cat) &&
    (status === 'All' || r.status === status.toLowerCase()) &&
    (!q.trim() || `${r.kb_id} ${r.title}`.toLowerCase().includes(q.trim().toLowerCase())));
  const s = data?.stats;

  return (
    <Shell user={user} active="/kb">
      <div className="page-head">
        <div>
          <div className="eyebrow muted">Knowledge base</div>
          <h1>Articles</h1>
        </div>
        {user.role === 'admin' && (
          <div className="dash-right">
            <button className="btn" onClick={reindex} disabled={busy}><Icon name="refresh" size={16} />Re-index all</button>
            <button className="btn primary" onClick={() => { setError(''); setModal(true); }}><Icon name="upload" size={16} />Upload article</button>
          </div>
        )}
      </div>
      <div className="scroll">
        <div className="content">
          <div className="stats">
            <div className="card stat"><div className="label">Documents</div><div className="value">{s?.documents ?? '-'}</div><div className="sub">All versions</div></div>
            <div className="card stat"><div className="label">Active</div><div className="value green">{s?.active ?? '-'}</div><div className="sub">Used for retrieval</div></div>
            <div className="card stat"><div className="label">Superseded</div><div className="value">{s?.superseded ?? '-'}</div><div className="sub">Filtered out of answers</div></div>
            <div className="card stat"><div className="label">Last indexed</div><div className="value" style={{ fontSize: 20 }}>{s?.last_index ? dateTime(s.last_index) : '-'}</div><div className="sub">Vector store: ChromaDB</div></div>
          </div>
          <div className="kb-layout">
            <div className="card table-card">
              <div className="filters">
                <div className="searchbox"><Icon name="search" size={17} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by ID or title" /></div>
                <select className="select" value={cat} onChange={(e) => setCat(e.target.value)} aria-label="Category">
                  {cats.map((c) => <option key={c}>{c}</option>)}
                </select>
                <select className="select" value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
                  {['All', 'Active', 'Superseded'].map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
              {shown.length === 0 ? <div className="empty"><b>No articles match</b>Change the search or filters.</div> : (
                <div style={{ overflowX: 'auto' }}>
                  <table className="t">
                    <thead><tr><th>ID</th><th>Title</th><th>Category</th><th>Version</th><th>Status</th><th>Updated</th></tr></thead>
                    <tbody>
                      {shown.map((r) => (
                        <tr key={r.id} style={r.status === 'superseded' ? { opacity: 0.65 } : null}>
                          <td className="id">{r.kb_id}</td>
                          <td><b>{r.title}</b></td>
                          <td>{r.category}</td>
                          <td>{r.version}</td>
                          <td><span className={`status ${r.status}`}>{r.status === 'active' ? 'Active' : 'Superseded'}</span></td>
                          <td style={{ whiteSpace: 'nowrap' }}>{dateTime(r.updated_at)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
            <div className="card test-card">
              <h3>Test retrieval</h3>
              <p className="desc">Run a question through the same search Ridley uses and see which chunks come back.</p>
              <form onSubmit={runTest} style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
                <input className="input" style={{ padding: '10px 14px', fontSize: 14 }} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Example: vpn keeps disconnecting" />
                <button className="btn primary" disabled={testing || !query.trim()}>{testing ? '...' : 'Run'}</button>
              </form>
              {result && (
                <>
                  <div className="small" style={{ color: 'var(--muted)', fontSize: 12.5, marginBottom: 10 }}>{result.results.length} chunks in {result.elapsed_ms} ms</div>
                  {result.results.length === 0 && <div className="empty">Nothing relevant found. Ridley would escalate this question.</div>}
                  {result.results.map((h, i) => (
                    <div key={`${h.kb_id}-${h.section}-${i}`} className={`hit ${i === 0 ? 'top' : ''}`}>
                      <div className="hh"><span>{h.kb_id} &middot; {h.title}</span><span>{h.score.toFixed(2)}</span></div>
                      <div className="sc"><i style={{ width: `${Math.min(100, h.score * 100)}%` }} /></div>
                      <span className="quote">{h.content.length > 170 ? `${h.content.slice(0, 170)}...` : h.content}</span>
                      <div className="sec">Section: {h.section} &middot; {h.version}</div>
                    </div>
                  ))}
                  {result.filtered.map((h) => (
                    <div key={`f-${h.kb_id}-${h.version}`} className="hit filtered">
                      <div className="hh"><span>{h.kb_id} &middot; {h.title}</span><span className="tagf">Filtered, superseded</span></div>
                      <span className="quote">{h.content.length > 120 ? `${h.content.slice(0, 120)}...` : h.content}</span>
                      <div className="sec">{h.version} was replaced by a newer version</div>
                    </div>
                  ))}
                  {result.answer && (
                    <>
                      <div className="eyebrow muted" style={{ margin: '14px 0 8px' }}>Answer preview</div>
                      <div className="suggest">{result.answer.replace(/\[\[t:[^\]]+\]\]/g, '')}</div>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
      {modal && (
        <div className="modal-bg" onClick={() => setModal(false)}>
          <form className="modal" onClick={(e) => e.stopPropagation()} onSubmit={upload}>
            <h3>Upload article</h3>
            <p className="sub">Using an existing KB ID creates a new version and retires the old one.</p>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <div className="field"><label>KB ID</label><input className="input" value={form.kb_id} onChange={(e) => setForm({ ...form, kb_id: e.target.value })} placeholder="KB-018" /></div>
              <div className="field"><label>Category</label><input className="input" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })} placeholder="Network" /></div>
            </div>
            <div className="field"><label>Title</label><input className="input" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div className="field"><label>Content</label><textarea className="input" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} placeholder={'## Summary\n...\n\n## Steps\n1. ...'} /></div>
            {error && <div style={{ color: 'var(--red)', fontSize: 13 }}>{error}</div>}
            <div className="foot">
              <button type="button" className="btn" onClick={() => setModal(false)}>Cancel</button>
              <button className="btn primary" disabled={busy}>{busy ? 'Indexing...' : 'Save and index'}</button>
            </div>
          </form>
        </div>
      )}
      {toast && <div className="toast">{toast}</div>}
    </Shell>
  );
}
