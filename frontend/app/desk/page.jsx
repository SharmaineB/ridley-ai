'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Shell from '@/components/Shell';
import Icon from '@/components/Icons';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';
import { timeOf } from '@/lib/format';

export default function Desk() {
  const user = useAuth(['technician', 'admin']);
  const [queue, setQueue] = useState([]);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [groups, setGroups] = useState([]);
  const [reply, setReply] = useState('');
  const [toast, setToast] = useState('');
  const endRef = useRef(null);

  const loadQueue = useCallback(async () => {
    try {
      const d = await api('/escalations');
      setQueue(d.escalations);
      setSelected((cur) => cur ?? d.escalations[0]?.escalation_id ?? null);
    } catch {}
  }, []);

  const loadDetail = useCallback(async (id) => {
    if (!id) return;
    try {
      setDetail(await api(`/escalations/${id}`));
    } catch {
      setDetail(null);
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    loadQueue();
    api('/meta/groups').then((d) => setGroups(d.groups)).catch(() => {});
    const t = setInterval(loadQueue, 6000);
    return () => clearInterval(t);
  }, [user, loadQueue]);

  useEffect(() => {
    if (!selected) return;
    loadDetail(selected);
    const t = setInterval(() => loadDetail(selected), 4000);
    return () => clearInterval(t);
  }, [selected, loadDetail]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [detail?.messages?.length]);

  function say(text) {
    setToast(text);
    setTimeout(() => setToast(''), 3500);
  }

  async function takeover() {
    await api(`/escalations/${selected}/takeover`, { method: 'POST' });
    say('You joined the chat');
    loadDetail(selected);
    loadQueue();
  }

  async function resolve() {
    await api(`/escalations/${selected}/resolve`, { method: 'POST' });
    say('Ticket resolved');
    setSelected(null);
    setDetail(null);
    await loadQueue();
  }

  async function reassign(group) {
    if (!group) return;
    await api(`/escalations/${selected}/reassign`, { method: 'POST', body: { group } });
    say(`Reassigned to ${group}`);
    loadDetail(selected);
    loadQueue();
  }

  async function send(e) {
    e.preventDefault();
    if (!reply.trim()) return;
    await api(`/escalations/${selected}/message`, { method: 'POST', body: { text: reply } });
    setReply('');
    loadDetail(selected);
  }

  if (!user) return null;
  const mine = detail && detail.technician_id === user.employee_id;
  const joined = detail && detail.technician_id;
  const firstName = detail ? detail.employee_name.split(' ')[0] : '';
  const sum = detail?.summary;

  return (
    <Shell user={user} active="/desk">
      <div className="desk">
        <div className="queue">
          <div className="eyebrow muted" style={{ padding: '2px 4px' }}>Escalation queue</div>
          {queue.length === 0 && <div className="empty"><b>Queue is clear</b>New escalations from Ridley show up here.</div>}
          {queue.map((q) => (
            <button key={q.escalation_id} className={`qcard ${q.priority} ${selected === q.escalation_id ? 'sel' : ''}`} onClick={() => { setSelected(q.escalation_id); setDetail(null); }}>
              <div className="top">
                <span className={`prio ${q.priority}`}>{q.priority === 'P1' ? 'P1 · CRITICAL' : q.priority}</span>
                <span>{q.wait_min} min</span>
              </div>
              <b>{q.employee_name}</b>
              <span className="issue">{q.issue}</span>
              {q.priority === 'P1' && q.ack_due && <span className="due">Security ack due in {q.ack_due}</span>}
              {q.status === 'In progress' && <span style={{ color: 'var(--teal)', fontWeight: 600, fontSize: 12.5, display: 'block', marginTop: 6 }}>In progress</span>}
            </button>
          ))}
        </div>

        {!detail ? (
          <div className="no-sel">{queue.length ? 'Loading conversation...' : 'Select an escalation to see the conversation.'}</div>
        ) : (
          <>
            <div className="convo">
              <div className="convo-head">
                <div>
                  <h2>{detail.employee_name} <span className={`prio ${detail.priority}`} style={{ marginLeft: 8 }}>{detail.priority}</span></h2>
                  <small>{detail.employee_id} &middot; {detail.ticket_id} &middot; {detail.assigned_group}</small>
                </div>
                <div className="acts">
                  {!joined && <button className="btn primary" style={{ whiteSpace: 'nowrap' }} onClick={takeover}>Take over chat</button>}
                  {joined && <button className="btn" style={{ whiteSpace: 'nowrap' }} onClick={resolve} disabled={!mine && user.role !== 'admin'}>Resolve</button>}
                  <select className="select" value="" onChange={(e) => reassign(e.target.value)} aria-label="Reassign">
                    <option value="">Reassign...</option>
                    {groups.map((g) => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
              </div>
              <div className="thread">
                <div className="thread-in">
                  {detail.messages.map((m) => {
                    if (m.sender === 'user') {
                      return (
                        <div className="row-user" key={m.message_id}>
                          <div className="bubble">{m.text}</div>
                          <span className="stamp" style={{ marginRight: 0 }}>{firstName} &middot; {timeOf(m.created_at)}</span>
                        </div>
                      );
                    }
                    if (m.sender === 'tech') {
                      return (
                        <div className="row-user" key={m.message_id} style={{ alignItems: 'flex-start' }}>
                          <div className="bubble tech">{m.text}</div>
                          <span className="stamp" style={{ marginRight: 0 }}>Technician &middot; {timeOf(m.created_at)}</span>
                        </div>
                      );
                    }
                    return m.blocks.map((b, i) => {
                      const key = `${m.message_id}-${i}`;
                      if (b.type === 'text') {
                        return (
                          <div className="ai-card" key={key} style={{ maxWidth: 560 }}>
                            <div className="who">RIDLEY AI</div>
                            <div className="txt">{b.text.replace(/\[\[t:[^\]]+\]\]/g, '')}</div>
                            {b.sources?.length > 0 && <div className="chips">{b.sources.map((s) => <span className="chip" key={s.kb_id}>{s.kb_id}</span>)}</div>}
                          </div>
                        );
                      }
                      if (b.type === 'guardrail') return <div className="guard" key={key}><Icon name="shield" size={15} />{b.text}</div>;
                      if (b.type === 'escalated') return <div className="wait" key={key}><i />{joined ? 'Technician joined' : `Waiting for a technician · ${detail.wait_min} min`}</div>;
                      if (b.type === 'joined') return <div className="joined" key={key}>{b.text}</div>;
                      if (b.type === 'success') return <div className="wait ok" key={key}>{b.title} &middot; {b.function}</div>;
                      return null;
                    });
                  })}
                  <div ref={endRef} />
                </div>
                <form className="composer-wrap" onSubmit={send}>
                  <div className="composer">
                    <input value={reply} onChange={(e) => setReply(e.target.value)} disabled={!joined} placeholder={joined ? `Reply to ${firstName}` : `Take over the chat to reply to ${firstName}`} />
                    <button className={`send ${reply.trim() ? 'on' : ''}`} disabled={!reply.trim() || !joined} aria-label="Send"><Icon name="send" size={18} /></button>
                  </div>
                </form>
              </div>
            </div>
            <aside className="summary">
              <h4>AI summary</h4>
              <p>{sum?.issue}</p>
              <h4>Steps tried</h4>
              <ul>{sum?.steps_tried?.map((s, i) => <li key={i}>{s}</li>)}</ul>
              <h4>Data checked</h4>
              <ul>{sum?.data_checked?.map((s, i) => <li key={i}>{s}</li>)}</ul>
              <h4>Recommended group</h4>
              <div className="grp">{sum?.recommended_group} <span className={`prio ${sum?.priority}`}>{sum?.priority}</span></div>
              <div className="small">{sum?.reason}{sum?.sources?.length ? ` Source ${sum.sources.join(', ')}.` : ''}</div>
              <h4>Suggested reply</h4>
              <div className="suggest">{sum?.suggested_reply}</div>
              <div className="suggest-actions">
                <button className="btn primary" disabled={!joined} onClick={() => setReply(sum?.suggested_reply || '')}>Insert</button>
                <button className="btn" onClick={() => loadDetail(selected)} aria-label="Refresh"><Icon name="refresh" size={16} /></button>
              </div>
              <div className="small" style={{ marginTop: 10 }}>Drafted from the knowledge base. Review before sending.</div>
            </aside>
          </>
        )}
      </div>
      {toast && <div className="toast">{toast}</div>}
    </Shell>
  );
}
