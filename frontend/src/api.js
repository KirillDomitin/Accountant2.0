const BASE = '/api/v1'

function parseDetail(detail) {
  if (!detail) return 'Ошибка запроса'
  if (typeof detail === 'string') return detail
  // FastAPI validation error: [{loc, msg, type}, ...]
  if (Array.isArray(detail)) {
    return detail.map(e => e.msg ?? JSON.stringify(e)).join('; ')
  }
  return JSON.stringify(detail)
}

async function extractError(res) {
  const body = await res.json().catch(() => null)
  if (!body) return `Ошибка ${res.status}`
  return parseDetail(body.detail)
}

export async function lookupInn(inn) {
  const res = await fetch(`${BASE}/inn/lookup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ inn }),
  })
  if (!res.ok) throw new Error(await extractError(res))
  const disposition = res.headers.get('Content-Disposition') || ''
  const match = disposition.match(/filename\*=UTF-8''(.+)/)
  const filename = match ? decodeURIComponent(match[1]) : `${inn}.docx`
  const blob = await res.blob()
  return { blob, filename }
}

export async function getHistory(offset = 0, limit = 10) {
  const res = await fetch(`${BASE}/history?offset=${offset}&limit=${limit}`)
  if (!res.ok) throw new Error('Ошибка загрузки истории')
  return res.json()
}

export async function getTracking() {
  const res = await fetch(`${BASE}/tracking`)
  if (!res.ok) throw new Error('Ошибка загрузки отслеживания')
  return res.json()
}

export async function addTracking(inn) {
  const res = await fetch(`${BASE}/tracking`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ inn }),
  })
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

export async function addTrackingBulk(inns) {
  const res = await fetch(`${BASE}/tracking/bulk`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ inns }),
  })
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

export async function deleteTracking(inn) {
  const res = await fetch(`${BASE}/tracking/${inn}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(await extractError(res))
}

export async function checkTracking(inn) {
  const res = await fetch(`${BASE}/tracking/${inn}/check`, { method: 'POST' })
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}

export async function confirmTracking(inn) {
  const res = await fetch(`${BASE}/tracking/${inn}/confirm`, { method: 'POST' })
  if (!res.ok) throw new Error(await extractError(res))
}

export async function getTrackingDetail(inn) {
  const res = await fetch(`${BASE}/tracking/${inn}`)
  if (!res.ok) throw new Error(await extractError(res))
  return res.json()
}
