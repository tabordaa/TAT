import { PersonAvatar } from './PersonAvatar'
import type { CalendarAbsence } from '../types/vacation'
import { todayInBogota } from '../utils/businessDays'

const WEEKDAYS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
const MAX_DESKTOP_AVATARS = 3
const MAX_MOBILE_AVATARS = 2
const dayLabel = new Intl.DateTimeFormat('es-CO', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

export interface DayPerson {
  id: string
  name: string
  hasPhoto: boolean
}

export interface Day {
  iso: string // YYYY-MM-DD
  dayOfMonth: number
  isWeekend: boolean
  holiday: string | null // its name, when the day is a holiday (HU-4.6)
  people: DayPerson[]
  names: string[]
}

/** The days of `month` ("YYYY-MM"), each with who is away on it. UTC throughout,
 * so the viewer's time zone cannot move a day. Weekends and holidays are never
 * marked as absences: vacations only count business days (HU-4.1 CA02, HU-4.6). */
export function buildMonth(
  month: string,
  absences: CalendarAbsence[],
  holidays: ReadonlyMap<string, string> = new Map(),
): Day[] {
  const year = Number(month.slice(0, 4))
  const number = Number(month.slice(5, 7))
  const total = new Date(Date.UTC(year, number, 0)).getUTCDate()
  const days: Day[] = []
  for (let dayOfMonth = 1; dayOfMonth <= total; dayOfMonth += 1) {
    const date = new Date(Date.UTC(year, number - 1, dayOfMonth))
    const iso = date.toISOString().slice(0, 10)
    const weekday = date.getUTCDay()
    const isWeekend = weekday === 0 || weekday === 6
    const holiday = holidays.get(iso) ?? null
    const people: DayPerson[] = []
    if (!isWeekend && holiday === null) {
      const seen = new Set<string>()
      for (const absence of absences) {
        // ISO dates compare correctly as plain strings.
        if (absence.start_date <= iso && iso <= absence.end_date && !seen.has(absence.employee_id)) {
          seen.add(absence.employee_id)
          people.push({
            id: absence.employee_id,
            name: absence.employee_name,
            hasPhoto: absence.has_photo,
          })
        }
      }
    }
    const names = people.map((person) => person.name)
    days.push({ iso, dayOfMonth, isWeekend, holiday, people, names })
  }
  return days
}

interface VacationCalendarProps {
  month: string
  absences: CalendarAbsence[]
  holidays?: ReadonlyMap<string, string>
  /** HU-4.8: a marked day can be chosen (click, Enter or Space) to see its count. */
  selectedDay?: string | null
  onSelectDay?: (iso: string) => void
}

// HU-4.4: a month as a CSS grid (CA01), Monday first. A marked day shows who is
// away on hover AND on keyboard focus (CA03): the names are also in its label,
// so a screen reader hears them without the tooltip.
export function VacationCalendar({
  month,
  absences,
  holidays,
  selectedDay = null,
  onSelectDay,
}: VacationCalendarProps) {
  const days = buildMonth(month, absences, holidays)
  const today = todayInBogota()
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
          const marked = day.people.length > 0
          const isToday = day.iso === today
          const label = dayLabel.format(new Date(`${day.iso}T00:00:00Z`))
          const tooltipId = `absence-${day.iso}`
          return (
            <div
              key={day.iso}
              role="gridcell"
              className={[
                'calendar-day',
                day.isWeekend ? 'calendar-weekend' : '',
                day.holiday !== null ? 'calendar-holiday' : '',
                marked ? 'calendar-marked' : '',
                isToday ? 'calendar-today' : '',
                day.iso === selectedDay ? 'calendar-selected' : '',
              ]
                .filter(Boolean)
                .join(' ')}
              tabIndex={marked ? 0 : undefined}
              aria-current={isToday ? 'date' : undefined}
              aria-selected={marked && onSelectDay !== undefined ? day.iso === selectedDay : undefined}
              onClick={marked && onSelectDay !== undefined ? () => onSelectDay(day.iso) : undefined}
              onKeyDown={
                marked && onSelectDay !== undefined
                  ? (event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        onSelectDay(day.iso)
                      }
                    }
                  : undefined
              }
              aria-label={
                day.holiday !== null
                  ? `${label}: festivo, ${day.holiday}`
                  : marked
                    ? `${label}: ${day.names.join(', ')}`
                    : `${label}: sin ausencias`
              }
              aria-describedby={marked ? tooltipId : undefined}
              data-date={day.iso}
            >
              <span className="calendar-number" aria-hidden="true">
                {day.dayOfMonth}
              </span>
              {day.holiday !== null && (
                <span className="calendar-holiday-name" aria-hidden="true">
                  {day.holiday}
                </span>
              )}
              {marked && (
                <>
                  <div className="calendar-avatars" aria-hidden="true">
                    {day.people.slice(0, MAX_DESKTOP_AVATARS).map((person, index) => (
                      <PersonAvatar
                        key={person.id}
                        id={person.id}
                        name={person.name}
                        hasPhoto={person.hasPhoto}
                        size="xs"
                        className={index >= MAX_MOBILE_AVATARS ? 'calendar-avatar-desktop-only' : undefined}
                      />
                    ))}
                    {day.people.length > MAX_DESKTOP_AVATARS && (
                      <span className="calendar-avatar-more calendar-avatar-more-desktop">
                        +{day.people.length - MAX_DESKTOP_AVATARS}
                      </span>
                    )}
                    {day.people.length > MAX_MOBILE_AVATARS && (
                      <span className="calendar-avatar-more calendar-avatar-more-mobile">
                        +{day.people.length - MAX_MOBILE_AVATARS}
                      </span>
                    )}
                  </div>
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
