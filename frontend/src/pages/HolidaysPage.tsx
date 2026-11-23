import { useEffect, useState, type FormEvent } from 'react'
import axios from 'axios'
import { addHoliday, getHolidays, removeHoliday } from '../api/holidays'
import { IconAlert, IconCheck } from '../components/Icons'
import type { Holiday } from '../types/holiday'
import { todayInBogota } from '../utils/businessDays'

const dateFormatter = new Intl.DateTimeFormat('es-CO', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
  timeZone: 'UTC',
})

function formatDay(day: string): string {
  const text = dateFormatter.format(new Date(`${day}T00:00:00Z`))
  return text.charAt(0).toUpperCase() + text.slice(1)
}

type Load = { phase: 'loading' } | { phase: 'error' } | { phase: 'ready'; holidays: Holiday[] }

interface Values {
  day: string
  name: string
}

// HU-4.6 CA01: the ADMIN keeps the holiday table, e.g. a day declared by decree.
// The seed has the calculated holidays; requests already made keep their count.
export function HolidaysPage() {
  const [year, setYear] = useState(() => Number(todayInBogota().slice(0, 4)))
  const [load, setLoad] = useState<Load>({ phase: 'loading' })
  const [version, setVersion] = useState(0)
  const [values, setValues] = useState<Values>({ day: '', name: '' })
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [confirmingDay, setConfirmingDay] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoad({ phase: 'loading' })
    getHolidays(year, controller.signal)
      .then((holidays) => setLoad({ phase: 'ready', holidays }))
      .catch((reason: unknown) => {
        if (!axios.isCancel(reason)) setLoad({ phase: 'error' })
      })
    return () => controller.abort()
  }, [year, version])

  async function handleAdd(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setNotice(null)
    const name = values.name.trim()
    if (values.day === '' || name.length < 3) {
      setError('Elige la fecha y escribe un nombre de al menos 3 caracteres.')
      return
    }
    setIsSaving(true)
    try {
      const created = await addHoliday({ day: values.day, name })
      setValues({ day: '', name: '' })
      setError(null)
      setNotice(`Festivo agregado: ${formatDay(created.day)}, ${created.name}.`)
      setYear(Number(created.day.slice(0, 4)))
      setVersion((count) => count + 1)
    } catch (reason) {
      const status = axios.isAxiosError(reason) ? reason.response?.status : undefined
      setError(
        status === 409 ? 'Ese día ya es festivo.' : 'No se pudo agregar el festivo. Revisa los datos.',
      )
    } finally {
      setIsSaving(false)
    }
  }

  async function handleRemove(holiday: Holiday) {
    setNotice(null)
    setError(null)
    try {
      await removeHoliday(holiday.day)
      setNotice(`Festivo eliminado: ${formatDay(holiday.day)}, ${holiday.name}.`)
    } catch {
      setError('No se pudo eliminar el festivo.')
    } finally {
      setConfirmingDay(null)
      setVersion((count) => count + 1)
    }
  }

  return (
    <section className="page-readable">
      <header className="page-header">
        <h1 className="page-title">Festivos</h1>
      </header>

      <div className="detail-sections">
        <form
          className="card detail-section"
          aria-labelledby="holiday-form-title"
          onSubmit={(event) => void handleAdd(event)}
          noValidate
        >
          <h2 id="holiday-form-title" className="section-kicker">
            AGREGAR FESTIVO
          </h2>
          <p className="field-help">
            Los festivos no cuentan como días de vacaciones. Las solicitudes ya hechas conservan sus
            días hábiles.
          </p>
          {error !== null && (
            <div className="alert alert-error" role="alert">
              <IconAlert size={20} />
              <div className="alert-body">
                <span>{error}</span>
              </div>
            </div>
          )}
          {notice !== null && (
            <div className="alert alert-success" role="status">
              <IconCheck size={20} />
              <div className="alert-body">
                <span>{notice}</span>
              </div>
            </div>
          )}
          <div className="form-grid">
            <div className="field">
              <div className="field-label-row">
                <label htmlFor="holiday-day">Fecha</label>
              </div>
              <input
                id="holiday-day"
                type="date"
                value={values.day}
                onChange={(event) =>
                  setValues((previous) => ({ ...previous, day: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <div className="field-label-row">
                <label htmlFor="holiday-name">Nombre</label>
              </div>
              <input
                id="holiday-name"
                type="text"
                maxLength={80}
                value={values.name}
                onChange={(event) =>
                  setValues((previous) => ({ ...previous, name: event.target.value }))
                }
              />
            </div>
          </div>
          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={isSaving}>
              {isSaving ? 'Guardando…' : 'Agregar festivo'}
            </button>
          </div>
        </form>

        <section className="card detail-section" aria-labelledby="holiday-list-title">
          <div className="calendar-toolbar">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setYear((current) => current - 1)}
            >
              ‹ Año anterior
            </button>
            <h2 id="holiday-list-title" className="calendar-title" aria-live="polite">
              Festivos de {year}
            </h2>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setYear((current) => current + 1)}
            >
              Año siguiente ›
            </button>
          </div>

          {load.phase === 'loading' && <p className="muted">Cargando festivos…</p>}
          {load.phase === 'error' && <p className="muted">No se pudieron cargar los festivos.</p>}
          {load.phase === 'ready' && load.holidays.length === 0 && (
            <p className="muted">No hay festivos registrados para {year}.</p>
          )}
          {load.phase === 'ready' && load.holidays.length > 0 && (
            <div className="table-wrap">
              <table className="table" aria-label={`Festivos de ${year}`}>
                <thead>
                  <tr>
                    <th scope="col">Fecha</th>
                    <th scope="col">Nombre</th>
                    <th scope="col" className="col-actions">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {load.holidays.map((holiday) => (
                    <tr key={holiday.day}>
                      <td>{formatDay(holiday.day)}</td>
                      <td>{holiday.name}</td>
                      <td className="col-actions">
                        {confirmingDay === holiday.day ? (
                          <div
                            className="row-actions"
                            role="group"
                            aria-label="Confirmar eliminación"
                          >
                            <button
                              type="button"
                              className="btn btn-danger"
                              onClick={() => void handleRemove(holiday)}
                            >
                              Sí, eliminar
                            </button>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              onClick={() => setConfirmingDay(null)}
                            >
                              No
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => setConfirmingDay(holiday.day)}
                            aria-label={`Eliminar festivo ${holiday.name}`}
                          >
                            Eliminar
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>
    </section>
  )
}
