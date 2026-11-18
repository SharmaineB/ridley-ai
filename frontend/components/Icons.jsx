const P = {
  plus: 'M12 5v14M5 12h14',
  ticket: 'M3 9a2 2 0 0 0 0 6v3h18v-3a2 2 0 0 1 0-6V6H3zM13 6v12',
  help: 'M12 17h.01M9.1 9a3 3 0 0 1 5.8 1c0 2-3 2.5-3 4.5M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18z',
  send: 'M22 2 11 13M22 2l-7 20-4-9-9-4z',
  clip: 'M21 12.5 12.5 21a5.5 5.5 0 0 1-8-8L13 4.5a3.7 3.7 0 0 1 5.3 5.2L10 18a1.8 1.8 0 0 1-2.6-2.6L15 8',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0',
  out: 'M7 17 17 7M8 7h9v9',
  book: 'M4 19.5V5a2 2 0 0 1 2-2h13v17H6.5A2.5 2.5 0 0 0 4 22.5M8 7h7',
  shield: 'M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z',
  bars: 'M4 20V10M10 20V4M16 20v-8M22 20H2',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  search: 'M11 19a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM21 21l-4.3-4.3',
  download: 'M12 3v12m0 0-4-4m4 4 4-4M4 21h16',
  upload: 'M12 15V3m0 0L8 7m4-4 4 4M4 21h16',
  refresh: 'M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5',
  calendar: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  alert: 'M12 8v5M12 17h.01M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
  check: 'M20 6 9 17l-5-5',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z',
  eyeoff: 'M3 3l18 18M10.6 6.1A9.8 9.8 0 0 1 12 6c6 0 10 6 10 6a17 17 0 0 1-3.2 3.7M6.6 6.6A17 17 0 0 0 2 12s4 7 10 7a9.5 9.5 0 0 0 4-.9M9.9 9.9a3 3 0 0 0 4.2 4.2',
  info: 'M12 16v-4M12 8h.01M12 22a10 10 0 1 0 0-20 10 10 0 0 0 0 20z',
  arrow: 'M5 12h14m-6-6 6 6-6 6',
  chat: 'M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z',
  up: 'M7 10v11H3V10zM7 10l4-8a2 2 0 0 1 3 2v4h6a2 2 0 0 1 2 2l-1.5 8a2 2 0 0 1-2 1.7H7',
  down: 'M17 14V3h4v11zM17 14l-4 8a2 2 0 0 1-3-2v-4H4a2 2 0 0 1-2-2l1.5-8A2 2 0 0 1 5.5 4H17',
  dots: 'M6 12h.01M12 12h.01M18 12h.01',
  swap: 'M7 4 3 8l4 4M3 8h14M17 20l4-4-4-4M21 16H7',
  chevron: 'M6 9l6 6 6-6',
};

export default function Icon({ name, size = 18, stroke = 1.8, ...rest }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...rest}>
      <path d={P[name]} />
    </svg>
  );
}

export function LogoMark({ size = 40 }) {
  return (
    <span className="logo-mark" style={{ width: size, height: size }}>
      <svg width={size * 0.6} height={size * 0.6} viewBox="0 0 24 24" fill="none" stroke="#0F5257" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6z" />
        <path d="M9 10h6M9 13h4" />
      </svg>
    </span>
  );
}
