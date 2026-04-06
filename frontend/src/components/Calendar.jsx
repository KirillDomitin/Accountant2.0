import { useState, useEffect, useMemo } from 'react'

const MONTH_NAMES_RU = {
  january: 'Январь', february: 'Февраль', march: 'Март',
  april: 'Апрель', may: 'Май', june: 'Июнь',
  july: 'Июль', august: 'Август', september: 'Сентябрь',
  october: 'Октябрь', november: 'Ноябрь', december: 'Декабрь',
}

const MONTH_INDEX = {
  january: 0, february: 1, march: 2, april: 3,
  may: 4, june: 5, july: 6, august: 7,
  september: 8, october: 9, november: 10, december: 11,
}

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']

function getFirstDay(year, monthName) {
  return (new Date(year, MONTH_INDEX[monthName], 1).getDay() + 6) % 7
}

function getDaysInMonth(year, monthName) {
  return new Date(year, MONTH_INDEX[monthName] + 1, 0).getDate()
}

function stripHtml(html) {
  const d = document.createElement('div')
  d.innerHTML = html
  return d.textContent || ''
}

function parseXml(text) {
  // Strip any non-XML prefix (e.g. browser annotation before the actual XML)
  const xmlStart = text.indexOf('<')
  const xmlText = xmlStart > 0 ? text.slice(xmlStart) : text

  const doc = new DOMParser().parseFromString(xmlText, 'text/xml')

  // Detect XML parse error
  const parseError = doc.querySelector('parsererror')
  if (parseError) throw new Error('XML parse error: ' + parseError.textContent.slice(0, 200))

  const yearEl = doc.querySelector('year')
  const year = parseInt(yearEl?.getAttribute('index') || '2026')

  const months = Array.from(doc.querySelectorAll('month')).map(m => {
    const name = m.getAttribute('name')
    const days = Array.from(m.querySelectorAll('day')).map(d => ({
      num: parseInt(d.getAttribute('num')),
      type: d.getAttribute('type'), // holiday | event | plain
      content: d.textContent.trim() || null,
    }))
    return { name, days }
  })

  return { year, months }
}

function buildGrid(month, year) {
  const firstDay = getFirstDay(year, month.name)
  const totalDays = getDaysInMonth(year, month.name)
  const dayMap = {}
  month.days.forEach(d => { dayMap[d.num] = d })

  const cells = []
  for (let i = 0; i < firstDay; i++) cells.push(null) // empty leading cells
  for (let d = 1; d <= totalDays; d++) {
    cells.push(dayMap[d] || { num: d, type: 'plain', content: null })
  }
  return cells
}

// ── Month card (one of 12) ────────────────────────────────────────────────────

function MonthCard({ month, year, todayNum, isTodayMonth, onDayClick }) {
  const cells = buildGrid(month, year)

  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-3">
      {/* Month title */}
      <div className="text-xs font-semibold text-slate-300 text-center mb-2 tracking-wide">
        {MONTH_NAMES_RU[month.name]}
      </div>

      {/* Weekday headers */}
      <div className="grid grid-cols-7 mb-1">
        {WEEKDAYS.map(d => (
          <div
            key={d}
            className="text-center text-slate-500"
            style={{ fontSize: '9px', lineHeight: '1.6' }}
          >
            {d[0]}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7">
        {cells.map((cell, i) => {
          if (!cell) return <div key={i} />

          const isToday   = isTodayMonth && cell.num === todayNum
          const isEvent   = cell.type === 'event'
          const isHoliday = cell.type === 'holiday'

          let bg = ''
          let text = 'text-slate-500'

          if (isHoliday) { bg = 'bg-rose-500/25'; text = 'text-rose-300' }
          if (isEvent)   { bg = 'bg-amber-500/25'; text = 'text-amber-300' }
          if (isToday)   { bg = isEvent ? 'bg-amber-500/50' : isHoliday ? 'bg-rose-500/50' : 'bg-cyan-500/30'; text = 'text-white font-bold' }

          return (
            <button
              key={i}
              onClick={() => isEvent && onDayClick(cell, month.name)}
              disabled={!isEvent}
              title={isEvent ? `${cell.num} ${MONTH_NAMES_RU[month.name]}: открыть события` : undefined}
              style={{ fontSize: '10px', lineHeight: '1', paddingTop: '3px', paddingBottom: '3px' }}
              className={[
                'flex items-center justify-center rounded',
                bg,
                text,
                isToday ? 'ring-1 ring-cyan-400' : '',
                isEvent ? 'cursor-pointer hover:brightness-125' : 'cursor-default',
              ].filter(Boolean).join(' ')}
            >
              {cell.num}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Event modal ───────────────────────────────────────────────────────────────

function EventModal({ day, monthName, year, onClose }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl max-h-4/5 rounded-3xl border border-white/10 bg-slate-900 shadow-2xl flex flex-col"
        style={{ maxHeight: '80vh' }}
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-white/10 shrink-0">
          <h3 className="font-semibold text-slate-100">
            {day.num} {MONTH_NAMES_RU[monthName]?.toLowerCase()} {year}
          </h3>
          <button
            onClick={onClose}
            className="rounded-xl border border-white/10 bg-slate-800 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-700 transition-colors"
          >
            Закрыть
          </button>
        </div>
        <div
          className="overflow-y-auto p-5 calendar-content"
          dangerouslySetInnerHTML={{ __html: day.content }}
        />
      </div>
    </div>
  )
}

// ── Search results ────────────────────────────────────────────────────────────

function SearchResults({ months, year, query, onDayClick }) {
  const results = useMemo(() => {
    if (query.length < 2) return []
    const q = query.toLowerCase()
    const found = []
    months.forEach(month => {
      month.days.filter(d => d.type === 'event' && d.content).forEach(d => {
        if (stripHtml(d.content).toLowerCase().includes(q)) {
          found.push({ month, day: d })
        }
      })
    })
    return found
  }, [months, query])

  if (query.length < 2) {
    return <p className="text-slate-500 text-sm">Введите минимум 2 символа для поиска</p>
  }
  if (results.length === 0) {
    return <p className="text-slate-500 text-sm">Ничего не найдено по запросу «{query}»</p>
  }

  return (
    <div>
      <p className="text-xs text-slate-500 mb-3">
        Найдено: {results.length} {results.length === 1 ? 'событие' : 'событий'}
      </p>
      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {results.map(({ month, day }, i) => {
          const plain = stripHtml(day.content)
          const idx   = plain.toLowerCase().indexOf(query.toLowerCase())
          const start = Math.max(0, idx - 50)
          const snippet =
            (start > 0 ? '…' : '') +
            plain.slice(start, idx + 120).trim() +
            (idx + 120 < plain.length ? '…' : '')

          return (
            <button
              key={i}
              onClick={() => onDayClick(day, month.name)}
              className="w-full text-left rounded-2xl border border-white/10 bg-slate-900/50 px-4 py-3 hover:border-amber-500/30 hover:bg-slate-800/50 transition-all"
            >
              <span className="text-amber-400 text-sm font-medium">
                {day.num} {MONTH_NAMES_RU[month.name]}
              </span>
              <p className="text-xs text-slate-400 mt-1 line-clamp-2">{snippet}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function CalendarSection() {
  const [data, setData]             = useState(null)
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [eventModal, setEventModal] = useState(null) // { day, monthName }

  useEffect(() => {
    fetch('/calendar_2026.xml')
      .then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.text() })
      .then(text => { setData(parseXml(text)); setLoading(false) })
      .catch(e  => { setError(e.message); setLoading(false) })
  }, [])

  const handleDayClick = (day, monthName) => setEventModal({ day, monthName })
  const clearSearch = () => setSearchQuery('')

  if (loading) {
    return (
      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl">
        <p className="text-slate-500 text-sm">Загрузка налогового календаря...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl">
        <p className="text-rose-400 text-sm">Ошибка загрузки календаря: {error}</p>
      </div>
    )
  }

  const today = new Date()
  const isTodayYear = today.getFullYear() === data.year

  const eventDaysCount = data.months.reduce(
    (acc, m) => acc + m.days.filter(d => d.type === 'event').length, 0
  )

  const isSearching = searchQuery.length > 0

  return (
    <div className="rounded-3xl border border-white/10 bg-white/5 p-5 shadow-xl">

      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between mb-5">
        <div>
          <h2 className="text-xl font-semibold">Налоговый календарь {data.year}</h2>
          <p className="text-sm text-slate-400 mt-1">{eventDaysCount} дней с событиями</p>
        </div>

        {/* Search */}
        <div className="relative">
          <input
            type="text"
            placeholder="Поиск событий..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            className="rounded-2xl border border-white/10 bg-slate-950/70 pl-4 pr-8 py-2 text-sm outline-none placeholder:text-slate-500 focus:border-cyan-500/50 transition-colors w-52"
          />
          {searchQuery && (
            <button
              onClick={clearSearch}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs leading-none"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Legend */}
      {!isSearching && (
        <div className="flex flex-wrap gap-5 mb-5">
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className="inline-block w-3 h-3 rounded bg-rose-500/60" /> Выходной
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className="inline-block w-3 h-3 rounded bg-amber-500/60" /> Событие (кликабельно)
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className="inline-block w-3 h-3 rounded bg-slate-700" /> Рабочий день
          </div>
          <div className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className="inline-block w-3 h-3 rounded ring-1 ring-cyan-400 bg-cyan-500/30" /> Сегодня
          </div>
        </div>
      )}

      {/* Search results */}
      {isSearching && (
        <SearchResults
          months={data.months}
          year={data.year}
          query={searchQuery}
          onDayClick={handleDayClick}
        />
      )}

      {/* 12 months grid */}
      {!isSearching && (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
          {data.months.map(month => {
            const isTodayMonth =
              isTodayYear && today.getMonth() === MONTH_INDEX[month.name]
            return (
              <MonthCard
                key={month.name}
                month={month}
                year={data.year}
                todayNum={isTodayMonth ? today.getDate() : null}
                isTodayMonth={isTodayMonth}
                onDayClick={handleDayClick}
              />
            )
          })}
        </div>
      )}

      {/* Event modal */}
      {eventModal && (
        <EventModal
          day={eventModal.day}
          monthName={eventModal.monthName}
          year={data.year}
          onClose={() => setEventModal(null)}
        />
      )}
    </div>
  )
}
