export function getToken() {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('ridley_token');
}

export function getUser() {
  if (typeof window === 'undefined') return null;
  try {
    return JSON.parse(localStorage.getItem('ridley_user') || 'null');
  } catch {
    return null;
  }
}

export function saveSession(token, user) {
  localStorage.setItem('ridley_token', token);
  localStorage.setItem('ridley_user', JSON.stringify(user));
}

export function clearSession() {
  localStorage.removeItem('ridley_token');
  localStorage.removeItem('ridley_user');
  localStorage.removeItem('ridley_conv');
}

export async function api(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  const res = await fetch(`/api${path}`, {
    ...options,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
  if (res.status === 401 && !path.startsWith('/auth/login')) {
    clearSession();
    if (typeof window !== 'undefined') window.location.href = '/login';
    throw new Error('Session expired');
  }
  if (!res.ok) {
    let detail = 'Something went wrong';
    try {
      detail = (await res.json()).detail || detail;
    } catch {}
    const err = new Error(detail);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

export async function download(path, filename) {
  const res = await fetch(`/api${path}`, { headers: { Authorization: `Bearer ${getToken()}` } });
  if (!res.ok) throw new Error('Export failed');
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function homeFor(role) {
  if (role === 'admin') return '/dashboard';
  if (role === 'technician') return '/desk';
  return '/chat';
}
