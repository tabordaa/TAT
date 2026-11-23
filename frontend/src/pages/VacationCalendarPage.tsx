import { useEffect, useState } from 'react'
import axios from 'axios'
import { getAreas } from '../api/employees'
import { getHolidayMap } from '../api/holidays'
import { getVacationCalendar } from '../api/vacations'
import { IconAlert } from '../components/Icons'
import { VacationCalendar, buildMonth } from '../components/VacationCalendar'
import type { CalendarAbsence } from '../types/vacation'
import { todayInBogota } from '../utils/businessDays'

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
            {selectedDay !== null && (
              <p className="alert alert-info" role="status">
                {absentSentence(
                  buildMonth(month, load.absences, load.holidays).find(
                    (day) => day.iso === selectedDay,
                  )?.names.length ?? 0,
                  area,
                  selectedDay,
                )}
              </p>
            )}
            <p className="field-help">
              Solo vacaciones aprobadas y días hábiles; los festivos aparecen en amarillo. Pasa el cursor o usa Tab sobre un día marcado
              para ver quién está ausente; haz clic (o Enter) para ver cuántos son.
            </p>

            <h3 className="section-kicker">AUSENCIAS DEL MES</h3>
            {load.absences.length === 0 ? (
              <p className="muted">No hay vacaciones aprobadas en {title.toLowerCase()}.</p>
            ) : (
              <ul className="absence-list" aria-label={`Ausencias de ${title}`}>
                {load.absences.map((absence) => (
                  <li key={absence.request_id}>
                    <strong>{absence.employee_name}</strong>: del{' '}
                    {shortDate.format(new Date(`${absence.start_date}T00:00:00Z`))} al{' '}
                    {shortDate.format(new Date(`${absence.end_date}T00:00:00Z`))}
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </div>
    </section>
  )
}
