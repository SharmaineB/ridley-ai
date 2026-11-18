'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Icon, { LogoMark } from './Icons';
import { api, clearSession } from '@/lib/api';

const NAV = {
  agent: [
    { href: '/chat', label: 'New chat', icon: 'plus', primary: true },
    { href: '/tickets', label: 'My tickets', icon: 'ticket', badge: 'tickets' },
    { href: '/help', label: 'Help', icon: 'help' },
  ],
  technician: [
    { href: '/desk', label: 'Escalations', icon: 'chat', badge: 'esc' },
    { href: '/all-tickets', label: 'All tickets', icon: 'ticket' },
    { href: '/kb', label: 'Knowledge base', icon: 'book' },
  ],
  admin: [
    { href: '/dashboard', label: 'Dashboard', icon: 'bars' },
    { href: '/kb', label: 'Knowledge base', icon: 'book' },
    { href: '/audit', label: 'Audit log', icon: 'shield' },
    { href: '/all-tickets', label: 'All tickets', icon: 'ticket' },
  ],
};

const SUB = { admin: 'ADMIN', technician: 'SERVICE DESK', agent: '' };

export default function Shell({ user, active, children, onNewChat }) {
  const router = useRouter();
  const [badges, setBadges] = useState({});

  useEffect(() => {
    if (!user) return;
    let stop = false;
    async function load() {
      try {
        if (user.role === 'agent') {
          const d = await api('/tickets');
          if (!stop) setBadges({ tickets: d.counts.open + d.counts.in_progress });
        } else if (user.role === 'technician') {
          const d = await api('/escalations');
          if (!stop) setBadges({ esc: d.waiting });
        }
      } catch {}
    }
    load();
    const t = setInterval(load, 10000);
    return () => {
      stop = true;
      clearInterval(t);
    };
  }, [user]);

  if (!user) return null;
  const items = NAV[user.role] || [];
  const avatarClass = user.role === 'admin' ? 'lav' : user.role === 'technician' ? 'mint' : '';

  function signOut() {
    clearSession();
    router.replace('/login');
  }

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <LogoMark size={42} />
          <div>
            <b>Ridley <span>AI</span></b>
            {SUB[user.role] && <small>{SUB[user.role]}</small>}
          </div>
        </div>
        <nav className="nav">
          {items.map((it) => {
            const cls = [it.primary ? 'primary' : '', active === it.href ? 'active' : ''].join(' ');
            const count = it.badge ? badges[it.badge] : 0;
            const body = (
              <>
                <Icon name={it.icon} size={19} />
                {it.label}
                {count > 0 && <span className={`badge ${it.badge === 'esc' ? 'red' : ''}`}>{count}</span>}
              </>
            );
            if (it.primary && onNewChat) {
              return (
                <button key={it.href} className={cls} onClick={onNewChat}>
                  {body}
                </button>
              );
            }
            return (
              <Link key={it.href} href={it.href} className={cls}>
                {body}
              </Link>
            );
          })}
        </nav>
        <div className="spacer" />
        <div className="userbox">
          <span className={`avatar ${avatarClass}`}>{user.initials}</span>
          <div className="who">
            <b>{user.full_name}</b>
            <small>{user.role === 'agent' ? user.employee_id : user.title}</small>
          </div>
          <button onClick={signOut} title="Sign out" aria-label="Sign out">
            <Icon name="out" size={16} />
          </button>
        </div>
      </aside>
      <div className="main">{children}</div>
    </div>
  );
}
