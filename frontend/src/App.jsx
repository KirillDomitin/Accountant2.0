import { useState, useEffect, useCallback } from 'react'
import * as api from './api'
import CalendarSection from './components/Calendar'

const TAG_STYLES = {
  success:   'bg-emerald-500/15 text-emerald-300 border-emerald-400/30',
  error:     'bg-rose-500/15 text-rose-300 border-rose-400/30',
  active:    'bg-emerald-500/15 text-emerald-300 border-emerald-400/30',
  inactive:  'bg-slate-500/15 text-slate-300 border-slate-400/30',
  changed:   'bg-amber-500/15 text-amber-300 border-amber-400/30',
  unchanged: 'bg-sky-500/15 text-sky-300 border-sky-400/30',
}

function tagStyle(type) {
  return TAG_STYLES[type] ?? 'bg-slate-500/15 text-slate-300 border-slate-400/30'
}

function sanitizeInn(value) {
  return value.replace(/\s/g, '').replace(/\D/g, '')
}

function validateInn(value) {
  if (!value) return ''
  if (value.length < 10) return `Слишком короткий ИНН — введено ${value.length} из минимум 10 цифр`
  if (value.length > 12) return `Слишком длинный ИНН — максимум 12 цифр`
  return ''
}

function parseInns(raw) {
  return [...new Set(
    raw.split(/[\s,;]+/).map(s => s.replace(/\D/g, '')).filter(s => /^\d{10}$|^\d{12}$/.test(s))
  )]
}

function formatDate(dateStr) {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  const now = new Date()
  const time = d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })
  if (d.toDateString() === now.toDateString()) return `Сегодня, ${time}`
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return `Вчера, ${time}`
  return d.toLocaleDateString('ru-RU')
}

function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return
    const t = setTimeout(onClose, 4500)
    return () => clearTimeout(t)
  }, [toast, onClose])

  if (!toast) return null
  const colors = toast.type === 'error'
    ? 'bg-rose-500/20 border-rose-400/30 text-rose-200'
    : 'bg-emerald-500/20 border-emerald-400/30 text-emerald-200'

  return (
    <div className={`fixed bottom-6 right-6 z-50 rounded-2xl border px-5 py-4 shadow-xl backdrop-blur-xl max-w-sm text-sm ${colors}`}>
      {toast.message}
    </div>
  )
}

// ── Login Page ────────────────────────────────────────────────────────────────

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!email || !password) return
    setLoading(true)
    setError('')
    try {
      const payload = await api.login(email, password)
      onLogin(payload)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex items-center justify-center p-6">
      <div className="w-full max-w-sm">
        <div className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl overflow-hidden">
          <div className="bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-violet-500/10 p-8">
            <div className="flex items-center gap-4 mb-8">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-500 text-xl font-bold shadow-lg select-none">
                А
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Платформа бухгалтера</p>
                <h1 className="text-xl font-semibold">Бухгалтер.Онлайн</h1>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <label className="text-xs text-slate-400 uppercase tracking-wide">Email</label>
                <input
                  type="email"
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none placeholder:text-slate-500 focus:border-cyan-500/50 transition-colors"
                  placeholder="user@example.com"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  autoFocus
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs text-slate-400 uppercase tracking-wide">Пароль</label>
                <input
                  type="password"
                  className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none placeholder:text-slate-500 focus:border-cyan-500/50 transition-colors"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                />
              </div>

              {error && (
                <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading || !email || !password}
                className="w-full rounded-2xl bg-cyan-500/90 px-6 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-cyan-400/90 transition-colors"
              >
                {loading ? 'Вход...' : 'Войти'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Admin: Users Panel ────────────────────────────────────────────────────────

function UsersPanel({ showToast }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(false)
  const [createModal, setCreateModal] = useState(false)

  const loadUsers = useCallback(async () => {
    setLoading(true)
    try {
      const data = await api.getUsers()
      setUsers(data)
    } catch (e) {
      showToast('error', e.message)
    } finally {
      setLoading(false)
    }
  }, [showToast])

  useEffect(() => { loadUsers() }, [loadUsers])

  const handleToggleActive = async (user) => {
    try {
      await api.setUserActive(user.id, !user.is_active)
      showToast('success', `Пользователь ${user.email} ${user.is_active ? 'деактивирован' : 'активирован'}`)
      loadUsers()
    } catch (e) {
      showToast('error', e.message)
    }
  }

  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h2 className="text-xl font-semibold">Пользователи</h2>
          <p className="text-sm text-slate-400 mt-1">Управление доступом</p>
        </div>
        <button
          onClick={() => setCreateModal(true)}
          className="rounded-2xl bg-cyan-500/90 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400/90 transition-colors"
        >
          + Создать
        </button>
      </div>

      <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/40">
        <div className="grid grid-cols-[1fr,0.5fr,0.5fr,0.4fr] gap-4 border-b border-white/10 px-5 py-4 text-xs uppercase tracking-wide text-slate-400">
          <div>Email</div>
          <div>Роль</div>
          <div>Статус</div>
          <div></div>
        </div>

        {loading && <div className="px-5 py-8 text-center text-slate-500">Загрузка...</div>}
        {!loading && users.length === 0 && (
          <div className="px-5 py-8 text-center text-slate-500">Нет пользователей</div>
        )}
        {users.map(user => (
          <div
            key={user.id}
            className="grid grid-cols-[1fr,0.5fr,0.5fr,0.4fr] gap-4 px-5 py-4 border-b border-white/5 last:border-b-0 items-center hover:bg-white/[0.03] transition-colors"
          >
            <div className="font-medium text-sm truncate">{user.email}</div>
            <div>
              <span className={`inline-flex rounded-full border px-3 py-1 text-xs ${user.role === 'admin' ? 'bg-violet-500/15 text-violet-300 border-violet-400/30' : tagStyle('active')}`}>
                {user.role === 'admin' ? 'Админ' : 'Пользователь'}
              </span>
            </div>
            <div>
              <span className={`inline-flex rounded-full border px-3 py-1 text-xs ${tagStyle(user.is_active ? 'active' : 'inactive')}`}>
                {user.is_active ? 'Активен' : 'Заблокирован'}
              </span>
            </div>
            <div>
              {user.role !== 'admin' && (
                <button
                  onClick={() => handleToggleActive(user)}
                  className={`rounded-xl border px-3 py-1.5 text-xs transition-colors ${
                    user.is_active
                      ? 'border-rose-400/20 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20'
                      : 'border-emerald-400/20 bg-emerald-500/10 text-emerald-300 hover:bg-emerald-500/20'
                  }`}
                >
                  {user.is_active ? 'Заблокировать' : 'Активировать'}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>

      {createModal && (
        <CreateUserModal
          onClose={() => setCreateModal(false)}
          onCreated={() => { setCreateModal(false); loadUsers() }}
          showToast={showToast}
        />
      )}
    </div>
  )
}

function CreateUserModal({ onClose, onCreated, showToast }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('user')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await api.createUser(email, password, role)
      showToast('success', `Пользователь ${email} создан`)
      onCreated()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-sm rounded-3xl border border-white/10 bg-slate-900 p-6 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold">Новый пользователь</h3>
          <button
            onClick={onClose}
            className="rounded-xl border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
          >
            Закрыть
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label className="text-xs text-slate-400 uppercase tracking-wide">Email</label>
            <input
              type="email"
              className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none placeholder:text-slate-500 focus:border-cyan-500/50 transition-colors text-sm"
              placeholder="user@example.com"
              value={email}
              onChange={e => setEmail(e.target.value)}
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-slate-400 uppercase tracking-wide">Пароль</label>
            <input
              type="password"
              className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none placeholder:text-slate-500 focus:border-cyan-500/50 transition-colors text-sm"
              placeholder="Минимум 8 символов"
              value={password}
              onChange={e => setPassword(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs text-slate-400 uppercase tracking-wide">Роль</label>
            <select
              className="w-full rounded-2xl border border-white/10 bg-slate-950/70 px-4 py-3 outline-none focus:border-cyan-500/50 transition-colors text-sm"
              value={role}
              onChange={e => setRole(e.target.value)}
            >
              <option value="user">Пользователь</option>
              <option value="admin">Администратор</option>
            </select>
          </div>

          {error && (
            <div className="rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !email || !password}
            className="w-full rounded-2xl bg-cyan-500/90 px-6 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-cyan-400/90 transition-colors"
          >
            {loading ? 'Создаю...' : 'Создать'}
          </button>
        </form>
      </div>
    </div>
  )
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function App() {
  // auth: null = initializing, false = not logged in, {sub, role} = logged in
  const [auth, setAuth] = useState(null)

  // Try to restore session from httpOnly cookie on mount
  useEffect(() => {
    api.tryRefresh().then(payload => setAuth(payload || false))
  }, [])

  const handleLogin = (payload) => setAuth(payload)

  const handleLogout = async () => {
    await api.logout()
    setAuth(false)
  }

  if (auth === null) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="text-slate-500 text-sm">Загрузка...</div>
      </div>
    )
  }

  if (auth === false) {
    return <LoginPage onLogin={handleLogin} />
  }

  return <MainApp auth={auth} onLogout={handleLogout} />
}

// ── Main App (authenticated) ──────────────────────────────────────────────────

function MainApp({ auth, onLogout }) {
  const isAdmin = auth.role === 'admin'

  // uuid → email map, populated only for admin
  const [userMap, setUserMap] = useState({})

  const [inn, setInn] = useState('')
  const [innValidationError, setInnValidationError] = useState('')
  const [lookupLoading, setLookupLoading] = useState(false)
  const [lookupError, setLookupError] = useState('')

  const [history, setHistory] = useState([])
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyLoading, setHistoryLoading] = useState(false)

  const [tracking, setTracking] = useState([])
  const [trackingLoading, setTrackingLoading] = useState(false)
  const [trackInn, setTrackInn] = useState('')
  const [trackAddLoading, setTrackAddLoading] = useState(false)
  const [bulkResult, setBulkResult] = useState(null)
  const [checkingInns, setCheckingInns] = useState(new Set())
  const [confirmingInns, setConfirmingInns] = useState(new Set())
  const [historyModal, setHistoryModal] = useState(null)

  const [toast, setToast] = useState(null)

  const showToast = useCallback((type, message) => setToast({ type, message }), [])
  const hideToast = useCallback(() => setToast(null), [])

  const handleUnauthorized = useCallback((e) => {
    if (e?.isUnauthorized) { onLogout(); return true }
    return false
  }, [onLogout])

  const loadHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const data = await api.getHistory(0, 10)
      setHistory(data.items)
      setHistoryTotal(data.total)
    } catch (e) {
      if (!handleUnauthorized(e)) { /* ignore */ }
    } finally {
      setHistoryLoading(false)
    }
  }, [handleUnauthorized])

  const loadTracking = useCallback(async () => {
    setTrackingLoading(true)
    try {
      const data = await api.getTracking()
      setTracking(data)
    } catch (e) {
      if (!handleUnauthorized(e)) { /* ignore */ }
    } finally {
      setTrackingLoading(false)
    }
  }, [handleUnauthorized])

  useEffect(() => {
    loadHistory()
    loadTracking()
  }, [loadHistory, loadTracking])

  useEffect(() => {
    if (!isAdmin) return
    api.getUsers().then(users => {
      const map = {}
      users.forEach(u => { map[u.id] = u.email })
      setUserMap(map)
    }).catch(() => {})
  }, [isAdmin])

  const handleInnChange = (e) => {
    const clean = sanitizeInn(e.target.value)
    setInn(clean)
    setInnValidationError(clean ? validateInn(clean) : '')
    setLookupError('')
  }

  const handleLookup = async () => {
    const error = validateInn(inn)
    if (error) { setInnValidationError(error); return }
    setLookupLoading(true)
    setLookupError('')
    try {
      const { blob, filename } = await api.lookupInn(inn)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      URL.revokeObjectURL(url)
      showToast('success', `Готово: ${filename}`)
      loadHistory()
    } catch (e) {
      if (!handleUnauthorized(e)) setLookupError(e.message)
    } finally {
      setLookupLoading(false)
    }
  }

  const parsedInns = parseInns(trackInn)
  const isBulk = parsedInns.length > 1
  const canSubmit = parsedInns.length > 0

  const handleAddTracking = async () => {
    if (!canSubmit) return
    setTrackAddLoading(true)
    setBulkResult(null)
    try {
      if (isBulk) {
        const data = await api.addTrackingBulk(parsedInns)
        setBulkResult(data)
        setTrackInn('')
        showToast('success', `Добавлено: ${data.added}${data.skipped ? `, пропущено: ${data.skipped}` : ''}${data.failed ? `, ошибок: ${data.failed}` : ''}`)
      } else {
        await api.addTracking(parsedInns[0])
        setTrackInn('')
        showToast('success', `ИНН ${parsedInns[0]} добавлен в отслеживание`)
      }
      loadTracking()
    } catch (e) {
      if (!handleUnauthorized(e)) showToast('error', e.message)
    } finally {
      setTrackAddLoading(false)
    }
  }

  const handleConfirmTracking = async (innVal) => {
    setConfirmingInns(prev => new Set(prev).add(innVal))
    try {
      await api.confirmTracking(innVal)
      showToast('success', `Данные по ИНН ${innVal} обновлены`)
      loadTracking()
    } catch (e) {
      if (!handleUnauthorized(e)) showToast('error', e.message)
    } finally {
      setConfirmingInns(prev => { const next = new Set(prev); next.delete(innVal); return next })
    }
  }

  const handleShowHistory = async (innVal, orgName) => {
    try {
      const data = await api.getTrackingDetail(innVal)
      setHistoryModal({ inn: innVal, orgName, changes: data.changes || [] })
    } catch (e) {
      if (!handleUnauthorized(e)) showToast('error', e.message)
    }
  }

  const handleDeleteTracking = async (innVal) => {
    try {
      await api.deleteTracking(innVal)
      showToast('success', `ИНН ${innVal} удалён из отслеживания`)
      loadTracking()
    } catch (e) {
      if (!handleUnauthorized(e)) showToast('error', e.message)
    }
  }

  const handleCheckTracking = async (innVal) => {
    setCheckingInns(prev => new Set(prev).add(innVal))
    try {
      const result = await api.checkTracking(innVal)
      showToast(result.changed ? 'changed' : 'success', result.message)
      loadTracking()
    } catch (e) {
      if (!handleUnauthorized(e)) showToast('error', e.message)
    } finally {
      setCheckingInns(prev => { const next = new Set(prev); next.delete(innVal); return next })
    }
  }

  const todayCount = history.filter(h =>
    new Date(h.created_at).toDateString() === new Date().toDateString()
  ).length
  const activeTrackingCount = tracking.filter(t => t.is_active).length

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 md:p-8">
      <Toast toast={toast} onClose={hideToast} />

      <div className="mx-auto max-w-7xl space-y-6">

        {/* ── Header ── */}
        <header className="rounded-3xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl overflow-hidden">
          <div className="bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-violet-500/10 p-6 md:p-8">
            <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-400 to-violet-500 text-2xl font-bold shadow-lg select-none">
                  А
                </div>
                <div>
                  <p className="text-sm uppercase tracking-[0.25em] text-slate-400">Платформа бухгалтера</p>
                  <h1 className="text-3xl md:text-4xl font-semibold">Бухгалтер.Онлайн</h1>
                  <p className="mt-1 text-slate-300">ЕГРЮЛ, документы, мониторинг изменений и налоговый календарь — всё в одном окне</p>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="rounded-2xl border border-white/10 bg-slate-900/60 px-4 py-3">
                    <div className="text-xs text-slate-400">Выписок сегодня</div>
                    <div className="mt-1 text-2xl font-semibold">{todayCount}</div>
                  </div>
                  <div className="rounded-2xl border border-white/10 bg-slate-900/60 px-4 py-3">
                    <div className="text-xs text-slate-400">Мониторинг ИНН</div>
                    <div className="mt-1 text-2xl font-semibold">{activeTrackingCount}</div>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-2 ml-2">
                  <div className="text-xs text-slate-400 text-right">
                    {auth.email || auth.sub?.slice(0, 8) + '…'}
                    <span className={`ml-2 inline-flex rounded-full border px-2 py-0.5 text-xs ${isAdmin ? 'bg-violet-500/15 text-violet-300 border-violet-400/30' : tagStyle('active')}`}>
                      {isAdmin ? 'Админ' : 'Пользователь'}
                    </span>
                  </div>
                  <button
                    onClick={onLogout}
                    className="rounded-xl border border-white/10 bg-slate-900/70 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800/70 transition-colors"
                  >
                    Выйти
                  </button>
                </div>
              </div>
            </div>
          </div>
        </header>

        {/* ── Admin: Users Panel ── */}
        {isAdmin && <UsersPanel showToast={showToast} />}

        {/* ── Tax Calendar ── */}
        <CalendarSection />

        {/* ── Main grid ── */}
        <section className="grid grid-cols-1 xl:grid-cols-12 gap-6">

          {/* Left column */}
          <div className="xl:col-span-8 space-y-6">

            {/* EGRUL lookup */}
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl">
              <div className="mb-5">
                <h2 className="text-xl font-semibold">Получение выписки ЕГРЮЛ</h2>
                <p className="text-sm text-slate-400 mt-1">Поиск по ИНН и скачивание пояснительной записки в формате DOCX</p>
              </div>

              <div className="flex gap-3">
                <div className="flex-1 space-y-2">
                  <input
                    className={`w-full rounded-2xl border bg-slate-950/70 px-4 py-3 outline-none placeholder:text-slate-500 transition-colors ${
                      innValidationError
                        ? 'border-rose-400/60 focus:border-rose-400'
                        : 'border-white/10 focus:border-cyan-500/50'
                    }`}
                    placeholder="Введите ИНН (10–12 цифр)"
                    value={inn}
                    onChange={handleInnChange}
                    onKeyDown={e => e.key === 'Enter' && handleLookup()}
                    maxLength={12}
                    inputMode="numeric"
                  />
                  {innValidationError && (
                    <p className="px-1 text-xs text-rose-400">{innValidationError}</p>
                  )}
                </div>
                <button
                  onClick={handleLookup}
                  disabled={lookupLoading || !inn || !!innValidationError}
                  className="self-start rounded-2xl bg-cyan-500/90 px-6 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-cyan-400/90 transition-colors whitespace-nowrap"
                >
                  {lookupLoading ? 'Загрузка...' : 'Скачать DOCX'}
                </button>
              </div>

              {lookupError && (
                <div className="mt-3 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
                  {lookupError}
                </div>
              )}
            </div>

            {/* History table */}
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl">
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-xl font-semibold">История запросов</h2>
                  <p className="text-sm text-slate-400 mt-1">
                    {historyTotal > 0 ? `Последние запросы — всего ${historyTotal}` : 'Последние запросы'}
                  </p>
                </div>
                <button
                  onClick={loadHistory}
                  className="rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-2 text-sm text-slate-200 hover:bg-slate-800/70 transition-colors"
                >
                  Обновить
                </button>
              </div>

              <div className="overflow-hidden rounded-3xl border border-white/10 bg-slate-950/40">
                <div className={`grid ${isAdmin ? 'grid-cols-[1fr,0.7fr,0.5fr,0.65fr,0.8fr]' : 'grid-cols-[1fr,0.7fr,0.5fr,0.65fr]'} gap-4 border-b border-white/10 px-5 py-4 text-xs uppercase tracking-wide text-slate-400`}>
                  <div>Компания</div>
                  <div>ИНН</div>
                  <div>Статус</div>
                  <div>Дата</div>
                  {isAdmin && <div>Пользователь</div>}
                </div>

                {historyLoading && (
                  <div className="px-5 py-8 text-center text-slate-500">Загрузка...</div>
                )}
                {!historyLoading && history.length === 0 && (
                  <div className="px-5 py-8 text-center text-slate-500">История пуста — сделайте первый запрос</div>
                )}
                {history.map(item => (
                  <div
                    key={item.id}
                    className={`grid ${isAdmin ? 'grid-cols-[1fr,0.7fr,0.5fr,0.65fr,0.8fr]' : 'grid-cols-[1fr,0.7fr,0.5fr,0.65fr]'} gap-4 px-5 py-4 border-b border-white/5 last:border-b-0 items-center hover:bg-white/[0.03] transition-colors`}
                  >
                    <div>
                      <div className="font-medium">{item.org_name || '—'}</div>
                      {item.error_message && (
                        <div className="text-xs text-rose-400 mt-1 truncate max-w-xs">{item.error_message}</div>
                      )}
                    </div>
                    <div className="text-slate-300 text-sm">{item.inn}</div>
                    <div>
                      <span className={`inline-flex rounded-full border px-3 py-1 text-xs ${tagStyle(item.status)}`}>
                        {item.status === 'success' ? 'Готово' : 'Ошибка'}
                      </span>
                    </div>
                    <div className="text-slate-400 text-sm">{formatDate(item.created_at)}</div>
                    {isAdmin && (
                      <div className="text-slate-400 text-xs truncate">
                        {item.user_id ? (userMap[item.user_id] || item.user_id.slice(0, 8) + '…') : '—'}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right column */}
          <div className="xl:col-span-4 space-y-6">

            {/* Tracking */}
            <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl">
              <div className="mb-5">
                <h2 className="text-xl font-semibold">Отслеживание изменений</h2>
                <p className="text-sm text-slate-400 mt-1">Ежедневный мониторинг выписок по ИНН</p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-slate-950/50 p-3 space-y-2">
                <textarea
                  className="w-full rounded-2xl border border-white/10 bg-slate-900/70 px-4 py-3 outline-none placeholder:text-slate-500 text-sm transition-colors focus:border-emerald-500/50 resize-none"
                  placeholder={"Введите один или несколько ИНН\n(через пробел, запятую или с новой строки)"}
                  rows={3}
                  value={trackInn}
                  onChange={e => { setTrackInn(e.target.value); setBulkResult(null) }}
                  onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey && !isBulk) { e.preventDefault(); handleAddTracking() } }}
                />
                <div className="flex items-center justify-between gap-2">
                  <div className="text-xs text-slate-500">
                    {parsedInns.length > 0
                      ? isBulk
                        ? <span className="text-emerald-400">Найдено {parsedInns.length} ИНН</span>
                        : <span className="text-slate-400">ИНН: {parsedInns[0]}</span>
                      : trackInn.trim()
                        ? <span className="text-rose-400">Нет корректных ИНН (10 или 12 цифр)</span>
                        : null
                    }
                  </div>
                  <button
                    onClick={handleAddTracking}
                    disabled={trackAddLoading || !canSubmit}
                    className="rounded-2xl bg-emerald-400 px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap hover:bg-emerald-300 transition-colors"
                  >
                    {trackAddLoading ? '...' : isBulk ? `+ Добавить ${parsedInns.length}` : '+ Добавить'}
                  </button>
                </div>
              </div>

              <div className="mt-4 space-y-3">
                {trackingLoading && (
                  <div className="text-center text-slate-500 py-4">Загрузка...</div>
                )}
                {!trackingLoading && tracking.length === 0 && (
                  <div className="text-center text-slate-500 py-6 text-sm">
                    Нет отслеживаемых ИНН
                  </div>
                )}
                {tracking.map(item => (
                  <div
                    key={item.id}
                    className={`rounded-2xl border p-4 ${item.has_pending_changes ? 'border-amber-400/30 bg-amber-500/5' : 'border-white/10 bg-slate-950/50'}`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <div className="font-medium text-sm truncate">{item.org_name || 'Неизвестно'}</div>
                        <div className="text-xs text-slate-400 mt-1">ИНН: {item.inn}</div>
                        {isAdmin && item.user_id && (
                          <div className="text-xs text-violet-400 mt-0.5 truncate">
                            {userMap[item.user_id] || item.user_id.slice(0, 8) + '…'}
                          </div>
                        )}
                      </div>
                      <span className={`inline-flex rounded-full border px-3 py-1 text-xs shrink-0 ${tagStyle(item.is_active ? 'active' : 'inactive')}`}>
                        {item.is_active ? 'Активно' : 'Пауза'}
                      </span>
                    </div>

                    {item.has_pending_changes && (
                      <div className="mt-2 rounded-xl border border-amber-400/20 bg-amber-500/10 px-3 py-2 space-y-1">
                        <div className="text-xs font-semibold text-amber-300">Обнаружены изменения:</div>
                        {(item.pending_changed_fields || []).map((c, i) => (
                          <div key={i} className="text-xs text-amber-200/80">
                            {c.old || c.new
                              ? <><span className="font-medium">{c.field}:</span> {c.old} → {c.new}</>
                              : <span className="font-medium">{c.field}</span>
                            }
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="mt-2 text-xs text-slate-500">
                      Проверено: {formatDate(item.last_checked_at)}
                    </div>

                    {item.has_pending_changes && (
                      <button
                        onClick={() => handleConfirmTracking(item.inn)}
                        disabled={confirmingInns.has(item.inn)}
                        className="mt-3 w-full rounded-xl border border-amber-400/30 bg-amber-500/15 px-3 py-2 text-xs font-semibold text-amber-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-amber-500/25 transition-colors"
                      >
                        {confirmingInns.has(item.inn) ? 'Обновляю...' : 'Обновить данные'}
                      </button>
                    )}

                    <div className="mt-3 flex gap-2">
                      <button
                        onClick={() => handleCheckTracking(item.inn)}
                        disabled={checkingInns.has(item.inn)}
                        className="flex-1 rounded-xl border border-white/10 bg-slate-900/70 px-3 py-2 text-xs text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-800/70 transition-colors"
                      >
                        {checkingInns.has(item.inn) ? 'Проверяю...' : 'Проверить сейчас'}
                      </button>
                      <button
                        onClick={() => handleShowHistory(item.inn, item.org_name)}
                        className="rounded-xl border border-white/10 bg-slate-900/70 px-3 py-2 text-xs text-slate-200 hover:bg-slate-800/70 transition-colors"
                      >
                        История
                      </button>
                      <button
                        onClick={() => handleDeleteTracking(item.inn)}
                        className="rounded-xl border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-xs text-rose-300 hover:bg-rose-500/20 transition-colors"
                      >
                        Удалить
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Quick actions */}
            <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-violet-500/10 to-sky-500/10 p-5 shadow-xl">
              <div className="text-sm uppercase tracking-[0.25em] text-violet-300 mb-3">Быстрые действия</div>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => document.querySelector('input[placeholder*="ИНН"]')?.focus()}
                  className="rounded-2xl border border-white/10 bg-slate-950/40 p-4 text-left hover:bg-white/5 transition-colors"
                >
                  <div className="font-medium text-sm">Новая выписка</div>
                  <div className="text-xs text-slate-400 mt-1">Поиск и скачивание</div>
                </button>
                <button
                  onClick={() => document.querySelector('textarea')?.focus()}
                  className="rounded-2xl border border-white/10 bg-slate-950/40 p-4 text-left hover:bg-white/5 transition-colors"
                >
                  <div className="font-medium text-sm">Мониторинг</div>
                  <div className="text-xs text-slate-400 mt-1">Добавить ИНН</div>
                </button>
              </div>
            </div>

          </div>
        </section>

      </div>

      {/* Bulk result modal */}
      {bulkResult && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
          onClick={() => setBulkResult(null)}
        >
          <div
            className="w-full max-w-md rounded-3xl border border-white/10 bg-slate-900 p-6 shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold">Результат добавления</h3>
                <div className="flex gap-3 mt-1 text-xs">
                  {bulkResult.added > 0 && <span className="text-emerald-400">Добавлено: {bulkResult.added}</span>}
                  {bulkResult.skipped > 0 && <span className="text-slate-400">Пропущено: {bulkResult.skipped}</span>}
                  {bulkResult.failed > 0 && <span className="text-rose-400">Ошибок: {bulkResult.failed}</span>}
                </div>
              </div>
              <button
                onClick={() => setBulkResult(null)}
                className="rounded-xl border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Закрыть
              </button>
            </div>

            <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
              {bulkResult.results.map(r => (
                <div
                  key={r.inn}
                  className={`flex items-center gap-3 rounded-2xl border px-4 py-3 ${
                    r.success
                      ? 'border-emerald-400/20 bg-emerald-500/5'
                      : r.error === 'Уже отслеживается'
                        ? 'border-white/10 bg-slate-950/50'
                        : 'border-rose-400/20 bg-rose-500/5'
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full shrink-0 ${
                    r.success ? 'bg-emerald-400' : r.error === 'Уже отслеживается' ? 'bg-slate-500' : 'bg-rose-400'
                  }`} />
                  <div className="min-w-0 flex-1">
                    <div className="text-sm font-medium">{r.org_name || r.inn}</div>
                    {r.org_name && <div className="text-xs text-slate-500">{r.inn}</div>}
                  </div>
                  <div className={`text-xs shrink-0 ${
                    r.success ? 'text-emerald-400' : r.error === 'Уже отслеживается' ? 'text-slate-500' : 'text-rose-400'
                  }`}>
                    {r.success ? 'Добавлено' : r.error}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* History modal */}
      {historyModal && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
          onClick={() => setHistoryModal(null)}
        >
          <div
            className="w-full max-w-lg rounded-3xl border border-white/10 bg-slate-900 p-6 shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold">{historyModal.orgName || historyModal.inn}</h3>
                <p className="text-xs text-slate-400 mt-1">История изменений</p>
              </div>
              <button
                onClick={() => setHistoryModal(null)}
                className="rounded-xl border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
              >
                Закрыть
              </button>
            </div>

            {historyModal.changes.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-sm">Изменений не зафиксировано</div>
            ) : (
              <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                {historyModal.changes.map(change => (
                  <div key={change.id} className="rounded-2xl border border-white/10 bg-slate-950/60 p-4">
                    <div className="mb-2">
                      <span className="text-xs text-slate-400">{formatDate(change.detected_at)}</span>
                    </div>
                    <div className="space-y-1">
                      {(change.change_description?.changed_fields || []).map((c, i) => (
                        <div key={i} className="text-xs text-slate-300">
                          {c.old || c.new
                            ? <><span className="text-amber-300 font-medium">{c.field}:</span> <span className="text-slate-400">{c.old}</span> → <span className="text-emerald-300">{c.new}</span></>
                            : <span className="text-amber-300 font-medium">{c.field}</span>
                          }
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
