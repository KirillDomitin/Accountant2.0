const BASE = '/api/v1'

// Access token lives only in JS memory (never localStorage/sessionStorage)
let accessToken = null

export function setAccessToken(token) { accessToken = token }
export function clearAccessToken() { accessToken = null }

function parseJwt(token) {
  try {
    return JSON.parse(atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')))
  } catch {
    return null
  }
}

export function getTokenPayload() {
  return accessToken ? parseJwt(accessToken) : null
}

function parseDetail(detail) {
  if (!detail) return 'Ошибка запроса'
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map(e => e.msg ?? JSON.stringify(e)).join('; ')
  return JSON.stringify(detail)
}

async function extractError(res) {
  const body = await res.json().catch(() => null)
  if (!body) return `Ошибка ${res.status}`
  return parseDetail(body.detail)
}

async function doRefresh() {
  const res = await fetch('/auth/refresh', { method: 'POST', credentials: 'include' })
  if (!res.ok) throw new Error('Session expired')
  const data = await res.json()
  accessToken = data.access_token
}

async function apiFetch(url, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers }
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`

  let res = await fetch(url, { ...options, headers, credentials: 'include' })

  if (res.status === 401) {
    try {
      await doRefresh()
      headers['Authorization'] = `Bearer ${accessToken}`
      res = await fetch(url, { ...options, headers, credentials: 'include' })
    } catch {
      clearAccessToken()
      const err = new Error('UNAUTHORIZED')
      err.isUnauthorized = true
      throw err
    }
  }

  return res
}

// ── Auth ────────────────────────────────────────────────────────────────────

export async function login(email, password) {
  const res = await fetch('/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
    credentials: 'include',
  })
  if (!res.ok) throw new Error(await extractError(res))
  const data = await res.json()
  accessToken = data.access_token
  return parseJwt(data.access_token)
}

export async function logout() {
  await fetch('/auth/logout', { method: 'POST', credentials: 'include' }).catch(() => {})
  accessToken = null
}

export async function tryRefresh() {
  try {
    await doRefresh()
    return parseJwt(accessToken)
  } catch {
    return null
  }
}

// ── Admin: users ─────────────────────────────────────────────────────────────

export async function getUsers() {
  const res = await apiFetch('/auth/users')
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

export async function createUser(email, password, role = 'user') {
  const res = await apiFetch('/auth/users', {
    method: 'POST',
    body: JSON.stringify({ email, password, role }),
  })
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

export async function setUserActive(userId, isActive) {
  const res = await apiFetch(`/auth/users/${userId}`, {
    method: 'PATCH',
    body: JSON.stringify({ is_active: isActive }),
  })
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

// ── INN ──────────────────────────────────────────────────────────────────────

export async function lookupInn(inn) {
  const headers = {}
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`

  let res = await fetch(`${BASE}/inn/lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    credentials: 'include',
    body: JSON.stringify({ inn }),
  })

  if (res.status === 401) {
    try {
      await doRefresh()
      headers['Authorization'] = `Bearer ${accessToken}`
      res = await fetch(`${BASE}/inn/lookup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers },
        credentials: 'include',
        body: JSON.stringify({ inn }),
      })
    } catch {
      clearAccessToken()
      const err = new Error('UNAUTHORIZED')
      err.isUnauthorized = true
      throw err
    }
  }

  if (!res.ok) throw new Error(await extractError(res))
  const disposition = res.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename\*=UTF-8''(.+)/)
  const filename = match ? decodeURIComponent(match[1]) : `${inn}.docx`
  const blob = await res.blob()
  return { blob, filename }
}

export async function getHistory(offset = 0, limit = 10) {
  const res = await apiFetch(`${BASE}/history?offset=${offset}&limit=${limit}`)
  if (!res.ok) throw new Error('Ошибка загрузки истории')
  return res.json()
}

export async function getTracking() {
  const res = await apiFetch(`${BASE}/tracking`)
  if (!res.ok) throw new Error('Ошибка загрузки отслеживания')
  return res.json()
}

export async function addTracking(inn) {
  const res = await apiFetch(`${BASE}/tracking`, {
    method: 'POST',
    body: JSON.stringify({ inn }),
  })
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

export async function addTrackingBulk(inns) {
  const res = await apiFetch(`${BASE}/tracking/bulk`, {
    method: 'POST',
    body: JSON.stringify({ inns }),
  })
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

export async function deleteTracking(inn) {
  const res = await apiFetch(`${BASE}/tracking/${inn}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await extractError(res))
}

export async function checkTracking(inn) {
  const res = await apiFetch(`${BASE}/tracking/${inn}/check`, { method: 'POST' })
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

export async function confirmTracking(inn) {
  const res = await apiFetch(`${BASE}/tracking/${inn}/confirm`, { method: 'POST' })
  if (!res.ok) throw new Error(await extractError(res))
}

export async function getTrackingDetail(inn) {
  const res = await apiFetch(`${BASE}/tracking/${inn}`)
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}
