import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAreas } from '../api/employees'
import { getHolidayMap } from '../api/holidays'
import { getVacationCalendar } from '../api/vacations'
import { IconAlert, IconCalendar } from '../components/Icons'
import { PersonAvatar } from '../components/PersonAvatar'
import { VacationCalendar, buildMonth } from '../components/VacationCalendar'
import type { CalendarAbsence } from '../types/vacation'
import { businessDaysBetween, todayInBogota } from '../utils/businessDays'

const monthTitle = new Intl.DateTimeFormat('es-CO', {
  month: 'long',
  year: 'numeric',
  timeZone: 'UTC',
})
const shortDate = new Intl.DateTimeFormat('es-CO', {
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
})

function shortDateParts(iso: string): { day: string; month: string } {
  const parts = shortDate.formatToParts(new Date(`${iso}T00:00:00Z`))
  const day = parts.find((part) => part.type === 'day')?.value ?? ''
  const month = (parts.find((part) => part.type === 'month')?.value ?? '').replace(/\.$/, '')
  return { day, month }
}

/** Short span like "23 → 27 nov" or "28 nov → 3 dic". */
function formatShortRange(start: string, end: string): string {
  const from = shortDateParts(start)
  if (start === end) return `${from.day} ${from.month}`
  const to = shortDateParts(end)
  if (start.slice(0, 7) === end.slice(0, 7)) return `${from.day} → ${to.day} ${to.month}`
  return `${from.day} ${from.month} → ${to.day} ${to.month}`
}

/** "2026-11" moved by `delta` months. */
function shiftMonth(month: string, delta: number): string {
  const year = Number(month.slice(0, 4))
  const number = Number(month.slice(5, 7))
  const date = new Date(Date.UTC(year, number - 1 + delta, 1))
  return date.toISOString().slice(0, 7)
}

function formatTitle(month: string): string {
  const text = monthTitle.format(new Date(`${month}-01T00:00:00Z`))
  return text.charAt(0).toUpperCase() + text.slice(1)
}

type Load =
  | { phase: 'loading' }
  | { phase: 'error' }
  | { phase: 'ready'; absences: CalendarAbsence[]; holidays: ReadonlyMap<string, string> }

const dayTitle = new Intl.DateTimeFormat('es-CO', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

/** HU-4.8 CA02: "2 personas del área Ventas ausentes el lunes, 10 de marzo." */
function absentSentence(count: number, area: string | null, day: string): string {
  const who = count === 1 ? '1 persona' : `${count} personas`
  const where = area === null ? 'de la empresa' : `del área ${area}`
  const absent = count === 1 ? 'ausente' : 'ausentes'
  return `${who} ${where} ${absent} el ${dayTitle.format(new Date(`${day}T00:00:00Z`))}.`
}

// HU-4.4: approved vacations, month by month, to plan operations.
// HU-4.8: filtered by area, so a team does not leave all at once.
export function VacationCalendarPage() {
  const [month, setMonth] = useState(() => todayInBogota().slice(0, 7))
  const [area, setArea] = useState<string | null>(null)
  const [areas, setAreas] = useState<string[]>([])
  const [selectedDay, setSelectedDay] = useState<string | null>(null)
  const [load, setLoad] = useState<Load>({ phase: 'loading' })
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    getAreas(controller.signal)
      .then(setAreas)
      .catch(() => undefined) // without the list the calendar still shows everybody
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    setLoad({ phase: 'loading' })
    setSelectedDay(null)
    Promise.all([
      getVacationCalendar(month, area, controller.signal),
      getHolidayMap([Number(month.slice(0, 4))], controller.signal),
    ])
      .then(([absences, holidays]) => setLoad({ phase: 'ready', absences, holidays }))
      .catch((error: unknown) => {
        if (!axios.isCancel(error)) setLoad({ phase: 'error' })
      })
    return () => controller.abort()
  }, [month, area, reloadCount])

  const title = formatTitle(month)
  const monthDays =
    load.phase === 'ready' ? buildMonth(month, load.absences, load.holidays) : []
  const holidaySet =
    load.phase === 'ready' ? new Set(load.holidays.keys()) : new Set<string>()
  const selectedDayInfo =
    selectedDay !== null ? (monthDays.find((day) => day.iso === selectedDay) ?? null) : null
  const selectedPeopleIds = new Set(selectedDayInfo?.people.map((person) => person.id) ?? [])
  const sortedAbsences =
    load.phase === 'ready'
      ? [...load.absences].sort((a, b) => {
          const byStart = a.start_date.localeCompare(b.start_date)
          if (byStart !== 0) return byStart
          return a.employee_name.localeCompare(b.employee_name, 'es-CO')
        })
      : []

  return (
    <section>
      <header className="page-header">
        <h1 className="page-title">Calendario de ausencias</h1>
      </header>

      <div className="card detail-section">
        <div className="calendar-toolbar">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setMonth((current) => shiftMonth(current, -1))}
          >
            ‹ Mes anterior
          </button>
          <h2 className="calendar-title" aria-live="polite">
            {title}
          </h2>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => setMonth((current) => shiftMonth(current, 1))}
          >
            Mes siguiente ›
          </button>
        </div>

        <div className="calendar-filters">
          <div className="field">
            <div className="field-label-row">
              <label htmlFor="calendar-area">Área</label>
            </div>
            <select
              id="calendar-area"
              value={area ?? ''}
              onChange={(event) => setArea(event.target.value === '' ? null : event.target.value)}
            >
              <option value="">Todas las áreas</option>
              {areas.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {load.phase === 'loading' && <p className="muted">Cargando calendario…</p>}
        {load.phase === 'error' && (
          <div className="alert alert-error" role="alert">
            <IconAlert size={20} />
            <div className="alert-body">
              <strong>No se pudo cargar el calendario.</strong>
            </div>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setReloadCount((count) => count + 1)}
            >
              Reintentar
            </button>
          </div>
        )}
        {load.phase === 'ready' && (
          <>
            <VacationCalendar
              month={month}
              absences={load.absences}
              holidays={load.holidays}
              selectedDay={selectedDay}
              onSelectDay={setSelectedDay}
            />
            <div className="calendar-footer">
              <div className="calendar-legend" role="group" aria-label="Leyenda del calendario">
                <span className="calendar-legend-item">
                  <span className="calendar-swatch calendar-swatch-holiday" aria-hidden="true" />
                  Festivo
                </span>
                <span className="calendar-legend-item">
                  <span className="calendar-swatch calendar-swatch-weekend" aria-hidden="true" />
                  Fin de semana
                </span>
                <span className="calendar-legend-item">
                  <span className="calendar-swatch calendar-swatch-marked" aria-hidden="true" />
                  Con ausencias
                </span>
                <span className="calendar-legend-item">
                  <span className="calendar-swatch calendar-swatch-today" aria-hidden="true" />
                  Hoy
                </span>
              </div>
              <p className="field-help">Haz clic en un día para ver quién está ausente.</p>
            </div>
            {selectedDay !== null && (
              <p className="alert alert-info" role="status">
                {absentSentence(selectedDayInfo?.people.length ?? 0, area, selectedDay)}
              </p>
            )}

            <h3 className="section-kicker">AUSENCIAS DEL MES</h3>
            {sortedAbsences.length === 0 ? (
              <div className="empty-state absence-empty">
                <IconCalendar size={32} />
                <p className="muted">No hay vacaciones aprobadas en {title.toLowerCase()}.</p>
              </div>
            ) : (
              <ul className="absence-cards" aria-label={`Ausencias de ${title}`}>
                {sortedAbsences.map((absence) => {
                  const days = businessDaysBetween(
                    absence.start_date,
                    absence.end_date,
                    holidaySet,
                  )
                  const isHighlighted =
                    selectedDay !== null &&
                    selectedPeopleIds.has(absence.employee_id) &&
                    absence.start_date <= selectedDay &&
                    selectedDay <= absence.end_date
                  return (
                    <li
                      key={absence.request_id}
                      className={
                        isHighlighted ? 'absence-card absence-card-highlighted' : 'absence-card'
                      }
                    >
                      <div className="absence-card-person">
                        <PersonAvatar
                          id={absence.employee_id}
                          name={absence.employee_name}
                          hasPhoto={absence.has_photo}
                          size="sm"
                        />
                        <div className="absence-card-identity">
                          <strong className="absence-card-name">{absence.employee_name}</strong>
                          <span className="absence-card-area">{absence.area}</span>
                        </div>
                      </div>
                      <div className="absence-card-meta">
                        <span className="absence-card-dates">
                          {formatShortRange(absence.start_date, absence.end_date)}
                        </span>
                        {days !== null && (
                          <span className="absence-card-days">
                            {days === 1 ? '1 día hábil' : `${days} días hábiles`}
                          </span>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </>
        )}
      </div>
    </section>
  )
}
