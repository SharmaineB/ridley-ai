'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import Shell from '@/components/Shell';
import Icon from '@/components/Icons';
import { api } from '@/lib/api';
import { useAuth } from '@/lib/useAuth';
import { dayTime, greeting, localizeTokens, timeOf } from '@/lib/format';

function Sources({ sources }) {
  if (!sources || !sources.length) return null;
  return (
    <div className="chips">
      {sources.map((s) => (
        <span key={s.kb_id} className="chip" title={s.title}>
          <Icon name="book" size={14} />
          {s.kb_id}
        </span>
      ))}
    </div>
  );
}

function OtpCard({ block, onVerify, disabled }) {
  const [digits, setDigits] = useState(['', '', '', '', '', '']);
  const [left, setLeft] = useState(block.expires_seconds || 300);
  const refs = useRef([]);

  useEffect(() => {
    refs.current[0]?.focus();
    const t = setInterval(() => setLeft((v) => Math.max(0, v - 1)), 1000);
    return () => clearInterval(t);
  }, []);

  function setAt(i, v) {
    const ch = v.replace(/\D/g, '').slice(-1);
    const next = [...digits];
    next[i] = ch;
    setDigits(next);
    if (ch && i < 5) refs.current[i + 1]?.focus();
    if (next.every(Boolean) && !disabled) onVerify(next.join(''));
  }

  function onKey(i, e) {
    if (e.key === 'Backspace' && !digits[i] && i > 0) refs.current[i - 1]?.focus();
  }

  function onPaste(e) {
    const t = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (t.length === 6) {
      e.preventDefault();
      setDigits(t.split(''));
      onVerify(t);
    }
  }

  const mm = String(Math.floor(left / 60));
  const ss = String(left % 60).padStart(2, '0');
  return (
    <div className="sub-card">
      <div className="head">
        <span className="ico">...</span>
        <div>
          <b>Enter verification code</b>
          <small>{block.retry ? 'Try the code again' : `Sent to your registered mobile number ${block.sent_to}`}</small>
        </div>
        {!block.retry && <span className="sent">Sent</span>}
      </div>
      <div className="otp" onPaste={onPaste}>
        {digits.map((d, i) => (
          <input key={i} ref={(el) => (refs.current[i] = el)} value={d} inputMode="numeric" maxLength={1} disabled={disabled}
            onChange={(e) => setAt(i, e.target.value)} onKeyDown={(e) => onKey(i, e)} aria-label={`Digit ${i + 1}`} />
        ))}
      </div>
      <div className="otp-foot">
        <span>{left > 0 ? `Code expires in ${mm}:${ss}` : 'Code expired. Ask me to send a new one.'}</span>
      </div>
      {block.demo_code && <div className="demo-code">Demo mode: your code is <b className="mono">{block.demo_code}</b></div>}
    </div>
  );
}

function Rating({ onRate }) {
  const [v, setV] = useState(null);
  return (
    <div className="thumbs">
      Was this helpful?
      <button className={v === 5 ? 'on' : ''} onClick={() => { setV(5); onRate(5); }} aria-label="Helpful"><Icon name="up" size={15} /></button>
      <button className={v === 1 ? 'on' : ''} onClick={() => { setV(1); onRate(1); }} aria-label="Not helpful"><Icon name="down" size={15} /></button>
    </div>
  );
}

export default function Chat() {
  const user = useAuth(['agent']);
  const [convId, setConvId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [human, setHuman] = useState(false);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [banner, setBanner] = useState(null);
  const [error, setError] = useState('');
  const endRef = useRef(null);
  const lastIdRef = useRef(0);

  useEffect(() => {
    if (!user) return;
    api('/banner').then((d) => setBanner(d.incident)).catch(() => {});
    const saved = localStorage.getItem('ridley_conv');
    if (saved) {
      api(`/conversations/${saved}`).then((d) => {
        setConvId(saved);
        setMessages(d.messages);
        setHuman(d.human_active);
      }).catch(() => localStorage.removeItem('ridley_conv'));
    }
  }, [user]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
    lastIdRef.current = messages.length ? messages[messages.length - 1].message_id : 0;
  }, [messages, busy]);

  useEffect(() => {
    if (!convId) return;
    const t = setInterval(async () => {
      try {
        const d = await api(`/conversations/${convId}`);
        setHuman(d.human_active);
        setMessages((cur) => {
          const curLast = cur.length ? cur[cur.length - 1].message_id : 0;
          const newLast = d.messages.length ? d.messages[d.messages.length - 1].message_id : 0;
          return newLast !== curLast || d.messages.length !== cur.length ? d.messages : cur;
        });
      } catch {}
    }, 4000);
    return () => clearInterval(t);
  }, [convId]);

  const send = useCallback(async (payload) => {
    setBusy(true);
    setError('');
    try {
      const d = await api('/chat', { method: 'POST', body: { conversation_id: convId, ...payload } });
      if (!convId) {
        setConvId(d.conversation_id);
        localStorage.setItem('ridley_conv', d.conversation_id);
      }
      setHuman(d.human_active);
      setMessages((cur) => {
        const known = new Set(cur.map((m) => m.message_id));
        return [...cur, ...d.messages.filter((m) => !known.has(m.message_id))];
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }, [convId]);

  function submit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput('');
    send({ message: text });
  }

  function newChat() {
    localStorage.removeItem('ridley_conv');
    setConvId(null);
    setMessages([]);
    setHuman(false);
    setInput('');
  }

  if (!user) return null;
  const lastIdx = messages.length - 1;

  return (
    <Shell user={user} active="/chat" onNewChat={newChat}>
      <div className="chat-head">
        <div>
          <div className="eyebrow online"><i />AI support online</div>
          <h1>{greeting()}, {user.first_name}</h1>
        </div>
        <div className="acct-chip">
          <span className="sq">{(user.account || 'T')[0]}</span>
          <div><b>{user.account || 'TaskUs'}</b><small><i />{user.work_mode} &middot; {user.site}</small></div>
        </div>
      </div>
      {banner && (
        <div className="banner">
          <span className="dot">!</span>
          <div><b>{banner.title}</b><small>{banner.id} &middot; Next update {banner.next_update}</small></div>
          <Link href="/help">View incident &rarr;</Link>
        </div>
      )}
      <div className="chat-main">
        <div className="thread">
          <div className="thread-in">
            {messages.length === 0 && (
              <div className="ai-card" style={{ marginLeft: 50 }}>
                <div className="who">RIDLEY AI</div>
                <div className="txt">Hi {user.first_name}. Tell me what is wrong, in English or Tagalog. I can unlock accounts, reset passwords, raise access requests and walk you through VPN, softphone and Citrix fixes. For anything else I will bring in a technician.</div>
              </div>
            )}
            {messages.length > 0 && <div className="divider">{dayTime(messages[0].created_at)}</div>}
            {messages.map((m, idx) => {
              if (m.sender === 'user') {
                return (
                  <div className="row-user" key={m.message_id}>
                    <div className="line">
                      <div className="bubble">{m.text}</div>
                      <span className="avatar sm">{user.initials}</span>
                    </div>
                    <span className="stamp">{timeOf(m.created_at)}</span>
                  </div>
                );
              }
              if (m.sender === 'tech') {
                return (
                  <div className="row-ai" key={m.message_id}>
                    <span className="ai-av" style={{ background: '#2a6e70' }}><Icon name="user" size={18} /></span>
                    <div className="ai-card">
                      <div className="who">TECHNICIAN &middot; {timeOf(m.created_at)}</div>
                      <div className="txt">{m.text}</div>
                    </div>
                  </div>
                );
              }
              return (
                <div key={m.message_id} style={{ display: 'contents' }}>
                  {m.blocks.map((b, i) => {
                    const key = `${m.message_id}-${i}`;
                    const active = idx === lastIdx;
                    if (b.type === 'text') {
                      return (
                        <div className="row-ai" key={key}>
                          <span className="ai-av"><Icon name="chat" size={18} /></span>
                          <div className="ai-card">
                            <div className="who">RIDLEY AI</div>
                            <div className="txt">{localizeTokens(b.text)}</div>
                            <Sources sources={b.sources} />
                            {b.actions && b.actions.length > 0 && active && !busy && !human && (
                              <div className="actions">
                                {b.actions.map((a) => (
                                  <button key={a.action + a.label} className={`btn ${a.style === 'primary' ? 'primary' : ''}`} onClick={() => send({ action: a.action })}>{a.label}</button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    }
                    if (b.type === 'otp') {
                      return <OtpCard key={key} block={b} disabled={!active || busy} onVerify={(code) => send({ action: 'verify', code })} />;
                    }
                    if (b.type === 'success') {
                      return (
                        <div className="sub-card success" key={key}>
                          <div className="head">
                            <span className="ico"><Icon name="check" size={20} stroke={2.4} /></span>
                            <div><b>{b.title}</b><small>{b.ticket_id} closed by Ridley</small></div>
                          </div>
                          <div style={{ fontSize: 14 }}>{b.text}</div>
                          {b.tip && <div className="tipbox"><b>TIP</b>{b.tip}</div>}
                          <Sources sources={b.sources} />
                          <Rating onRate={(v) => send({ action: 'rate', value: v })} />
                        </div>
                      );
                    }
                    if (b.type === 'guardrail') {
                      return <div className="guard" key={key}><Icon name="shield" size={15} />{b.text}</div>;
                    }
                    if (b.type === 'escalated') {
                      return <div className="wait" key={key}><i />{b.text} &middot; {b.ticket_id} &middot; {b.priority}</div>;
                    }
                    if (b.type === 'joined') {
                      return <div className="joined" key={key}>{b.text}</div>;
                    }
                    return null;
                  })}
                </div>
              );
            })}
            {busy && (
              <div className="row-ai">
                <span className="ai-av"><Icon name="chat" size={18} /></span>
                <div className="ai-card" style={{ padding: '14px 22px', width: 'auto' }}><span className="typing"><i /><i /><i /></span></div>
              </div>
            )}
            {error && <div className="alert err" style={{ maxWidth: 520 }}><Icon name="alert" size={18} /><div>{error}</div></div>}
            <div ref={endRef} />
          </div>
        </div>
        <div className="composer-wrap">
          <form className="composer" onSubmit={submit}>
            <span className="clip" title="Attachments are disabled"><Icon name="clip" /></span>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={human ? 'A technician is handling this chat. Add a message here.' : 'Message Ridley AI...'} aria-label="Message" />
            <button className={`send ${input.trim() ? 'on' : ''}`} disabled={!input.trim() || busy} aria-label="Send"><Icon name="send" size={18} /></button>
          </form>
          <div className="composer-foot">
            <span>Ridley can make mistakes. Check important information.</span>
            <button onClick={() => send({ action: 'human' })} disabled={busy || human}><Icon name="user" size={14} />Talk to a human</button>
          </div>
        </div>
      </div>
    </Shell>
  );
}
