const BASE = import.meta.env.VITE_API_BASE || '/api/v1'

export function getToken() {
  return localStorage.getItem('fs_token')
}
export function setToken(t) {
  if (t) localStorage.setItem('fs_token', t)
  else localStorage.removeItem('fs_token')
}
export function getUser() {
  try {
    return JSON.parse(localStorage.getItem('fs_user') || 'null')
  } catch {
    return null
  }
}
export function setUser(u) {
  if (u) localStorage.setItem('fs_user', JSON.stringify(u))
  else localStorage.removeItem('fs_user')
}
export function isAuthed() {
  return !!getToken()
}

async function request(path, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  if (res.status === 401) {
    setToken(null)
    if (!window.location.hash.includes('login')) window.location.hash = '#/login'
    throw new Error('Session expired')
  }

  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error(data.message || `Request failed (${res.status})`)
  return data
}

export const api = {
  get: (p) => request(p),
  post: (p, b) => request(p, { method: 'POST', body: b }),
  put: (p, b) => request(p, { method: 'PUT', body: b }),
  del: (p) => request(p, { method: 'DELETE' }),
}

export const fmtDate = (iso) => {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('en-KE', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

export const fmtTime = (iso) => {
  if (!iso) return '—'
  return new Date(iso).toLocaleTimeString('en-KE', {
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

export const money = (n) =>
  `KES ${Number(n || 0).toLocaleString('en-KE', { maximumFractionDigits: 0 })}`

export function levelColor(level) {
  return {
    safe: '#22c55e',
    suspicious: '#f59e0b',
    flagged: '#ef4444',
  }[level] || '#64748b'
}

export function severityColor(sev) {
  return {
    INFO: '#38bdf8',
    LOW: '#a3e635',
    MEDIUM: '#f59e0b',
    HIGH: '#fb7185',
    CRITICAL: '#ef4444',
  }[sev] || '#64748b'
}
