// Mirrors business_days() in backend/app/services/vacations.py. UX only: it
// shows the count while the dates are chosen; the server counts again on submit.

const DAY_MS = 24 * 60 * 60 * 1000

/** "YYYY-MM-DD" as a UTC date, so the viewer's time zone cannot shift the day. */
function parseDate(value: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null
  const date = new Date(`${value}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? null : date
}

/** Monday to Friday between both dates, inclusive; null if a date is missing or invalid. */
export function businessDaysBetween(start: string, end: string): number | null {
  const from = parseDate(start)
  const to = parseDate(end)
  if (from === null || to === null) return null
  if (to < from) return 0
  const total = Math.round((to.getTime() - from.getTime()) / DAY_MS) + 1
  const fullWeeks = Math.floor(total / 7)
  let count = fullWeeks * 5
  for (let offset = 0; offset < total % 7; offset += 1) {
    const day = new Date(from.getTime() + (fullWeeks * 7 + offset) * DAY_MS).getUTCDay()
    if (day !== 0 && day !== 6) count += 1
  }
  return count
}

/** Today's business date in Colombia, as "YYYY-MM-DD" (like the server's clock.today()). */
export function todayInBogota(): string {
  // en-CA formats dates as YYYY-MM-DD.
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Bogota' }).format(new Date())
}
