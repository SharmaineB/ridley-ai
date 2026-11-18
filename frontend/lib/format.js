export function timeOf(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export function dateTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ', ' + d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
}

export function dayTime(iso) {
  const d = new Date(iso);
  const today = new Date();
  const same = d.toDateString() === today.toDateString();
  return (same ? 'Today' : d.toLocaleDateString([], { month: 'short', day: 'numeric' })) + ', ' + timeOf(iso);
}

export function greeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 18) return 'Good afternoon';
  return 'Good evening';
}

export function localizeTokens(text) {
  return (text || '').replace(/\[\[t:([^\]]+)\]\]/g, (_, iso) => timeOf(iso));
}

export function rangeLabel(r) {
  if (!r) return '';
  const o = { month: 'short', day: 'numeric' };
  const a = new Date(r.start).toLocaleDateString([], o);
  const b = new Date(r.end).toLocaleDateString([], { ...o, year: 'numeric' });
  return `${a} – ${b}`;
}
