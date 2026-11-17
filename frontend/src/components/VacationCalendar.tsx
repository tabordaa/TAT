import type { CalendarAbsence } from '../types/vacation'

const WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const dayLabel = new Intl.DateTimeFormat('es-CO', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

interface Day {
  iso: string // YYYY-MM-DD
  dayOfMonth: number
  isWeekend: boolean
  names: string[]
}

/** The days of `month` ("YYYY-MM"), each with who is away on it. UTC throughout,
 * so the viewer's time zone cannot move a day. Weekends are never marked:
 * vacations only count business days (HU-4.1 CA02). */
export function buildMonth(month: string, absences: CalendarAbsence[]): Day[] {
  const year = Number(month.slice(0, 4))
  const number = Number(month.slice(5, 7))
  const total = new Date(Date.UTC(year, number, 0)).getUTCDate()
  const days: Day[] = []
  for (let dayOfMonth = 1; dayOfMonth <= total; dayOfMonth += 1) {
    const date = new Date(Date.UTC(year, number - 1, dayOfMonth))
    const iso = date.toISOString().slice(0, 10)
    const weekday = date.getUTCDay()
    const isWeekend = weekday === 0 || weekday === 6
    const names = isWeekend
      ? []
      : absences
          // ISO dates compare correctly as plain strings.
          .filter((absence) => absence.start_date <= iso && iso <= absence.end_date)
          .map((absence) => absence.employee_name)
    days.push({ iso, dayOfMonth, isWeekend, names })
  }
  return days
}

interface VacationCalendarProps {
  month: string
  absences: CalendarAbsence[]
}

// HU-4.4: a month as a CSS grid (CA01), Monday first. A marked day shows who is
// away on hover AND on keyboard focus (CA03): the names are also in its label,
// so a screen reader hears them without the tooltip.
export function VacationCalendar({ month, absences }: VacationCalendarProps) {
  const days = buildMonth(month, absences)
  // Empty cells before day 1 so it falls under its weekday (Monday = column 1).
  const firstWeekday = (new Date(`${month}-01T00:00:00Z`).getUTCDay() + 6) % 7

  return (
    <div className="calendar" role="grid" aria-label="Calendario de ausencias">
      <div className="calendar-row" role="row">
        {WEEKDAYS.map((name) => (
          <div key={name} className="calendar-weekday" role="columnheader">
            {name}
          </div>
        ))}
      </div>
      <div className="calendar-days" role="rowgroup">
        {Array.from({ length: firstWeekday }, (_, index) => (
          <div key={`blank-${index}`} className="calendar-blank" aria-hidden="true" />
        ))}
        {days.map((day) => {
          const marked = day.names.length > 0
          const label = dayLabel.format(new Date(`${day.iso}T00:00:00Z`))
          const tooltipId = `absence-${day.iso}`
          return (
            <div
              key={day.iso}
              role="gridcell"
              className={[
                'calendar-day',
                day.isWeekend ? 'calendar-weekend' : '',
                marked ? 'calendar-marked' : '',
              ].join(' ')}
              tabIndex={marked ? 0 : undefined}
              aria-label={
                marked ? `${label}: ${day.names.join(', ')}` : `${label}: sin ausencias`
              }
              aria-describedby={marked ? tooltipId : undefined}
              data-date={day.iso}
            >
              <span className="calendar-number" aria-hidden="true">
                {day.dayOfMonth}
              </span>
              {marked && (
                <>
                  <span className="calendar-count" aria-hidden="true">
                    {day.names.length === 1 ? '1 ausente' : `${day.names.length} ausentes`}
                  </span>
                  <span className="calendar-tooltip" role="tooltip" id={tooltipId}>
                    {day.names.join(', ')}
                  </span>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
