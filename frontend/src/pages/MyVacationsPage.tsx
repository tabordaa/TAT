import { useEffect, useState, type FormEvent } from 'react'
import axios from 'axios'
import {
  cancelMyVacationRequest,
  createVacationRequest,
  getMyVacationRequests,
} from '../api/vacations'
import { IconAlert, IconCalendar, IconCheck } from '../components/Icons'
import { VacationBalanceCard } from '../components/VacationBalanceCard'
import { getHolidayMap } from '../api/holidays'
import {
  VACATION_STATUS_LABELS,
  type VacationBalance,
  type VacationRequest,
  type VacationStatus,
} from '../types/vacation'
import { businessDaysBetween, todayInBogota } from '../utils/businessDays'

const dateFormatter = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeZone: 'UTC' })
const instantFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeZone: 'America/Bogota',
})

function formatDate(value: string): string {
  return dateFormatter.format(new Date(`${value}T00:00:00Z`))
}

const STATUS_BADGES: Record<VacationStatus, string> = {
  PENDIENTE: 'badge badge-warning',
  APROBADA: 'badge badge-success',
  RECHAZADA: 'badge badge-danger',
  CANCELADA: 'badge badge-muted',
}

interface Values {
  start: string
  end: string
}

type Errors = Partial<Record<keyof Values, string>>

type Requests =
  | { phase: 'loading' }
  | { phase: 'not-linked' }
  | { phase: 'error' }
  | { phase: 'ready'; requests: VacationRequest[] }

/** HU-4.5 CA01, mirrors can_be_cancelled() in the API: pending, or approved and not started. */
function canCancel(request: VacationRequest, today: string): boolean {
  if (request.status === 'PENDIENTE') return true
  return request.status === 'APROBADA' && request.start_date > today
}

/** UX only: the same rules the API applies, so most mistakes show before sending. */
function validate(values: Values, days: number | null, balance: VacationBalance | null): Errors {
  const errors: Errors = {}
  if (values.start === '') errors.start = 'Elige la fecha de inicio.'
  else if (values.start < todayInBogota()) errors.start = 'No puede empezar en el pasado.'
  if (values.end === '') errors.end = 'Elige la fecha de fin.'
  else if (values.start !== '' && values.end < values.start)
    errors.end = 'La fecha de fin no puede ser anterior a la de inicio.'
  else if (days === 0) errors.end = 'El rango no tiene días hábiles (solo fines de semana o festivos).'
  else if (days !== null && balance !== null && days > Number(balance.requestable_days))
    errors.end = `Superas tus días disponibles para solicitar (${balance.requestable_days}).`
  return errors
}

/** The API answers {field, message}; each case gets a message in Spanish. */
function serverErrors(error: unknown): { errors: Errors; message: string | null } {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const detail: unknown = error.response?.data?.detail
    const field =
      typeof detail === 'object' && detail !== null && 'field' in detail ? String(detail.field) : ''
    if (status === 409 && field === 'business_days')
      return { errors: { end: 'Superas tus días disponibles para solicitar.' }, message: null }
    if (status === 409 && field === 'start_date')
      return { errors: { start: 'Se cruza con otra solicitud pendiente o aprobada.' }, message: null }
    if (status === 409 && field === 'status')
      return { errors: {}, message: 'Solo un empleado activo con contrato vigente puede solicitar vacaciones.' }
    if (status === 422 && field === 'start_date')
      return { errors: { start: 'No puede empezar en el pasado.' }, message: null }
    if (status === 422 && field === 'end_date')
      return {
        errors: { end: 'El rango no tiene días hábiles o termina después de tu contrato.' },
        message: null,
      }
    if (status === 422) return { errors: {}, message: 'El servidor rechazó las fechas. Revísalas.' }
  }
  return { errors: {}, message: 'No se pudo enviar la solicitud. Inténtalo de nuevo.' }
}

// HU-4.1: the employee picks a range in a calendar (CA01), sees its business days
// (CA02) and sends it; it stays PENDIENTE (CA04). The API enforces CA03.
export function MyVacationsPage() {
  const [values, setValues] = useState<Values>({ start: '', end: '' })
  const [errors, setErrors] = useState<Errors>({})
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)
  const [isSending, setIsSending] = useState(false)
  const [balance, setBalance] = useState<VacationBalance | null>(null)
  const [requests, setRequests] = useState<Requests>({ phase: 'loading' })
  // Bumped after each request: the balance and the list are fetched again.
  const [version, setVersion] = useState(0)
  // HU-4.5: the request whose cancellation is being confirmed in its own row.
  const [confirmingId, setConfirmingId] = useState<string | null>(null)
  const [cancellingId, setCancellingId] = useState<string | null>(null)
  // HU-4.6: this year's and next year's holidays, so the count matches the server's.
  // If they fail to load the form still works: the server counts again on submit.
  const [holidays, setHolidays] = useState<ReadonlyMap<string, string>>(new Map())

  useEffect(() => {
    const controller = new AbortController()
    const year = Number(todayInBogota().slice(0, 4))
    getHolidayMap([year, year + 1], controller.signal)
      .then(setHolidays)
      .catch(() => undefined)
    return () => controller.abort()
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    getMyVacationRequests(controller.signal)
      .then((list) => setRequests({ phase: 'ready', requests: list }))
      .catch((error: unknown) => {
        if (axios.isCancel(error)) return
        if (axios.isAxiosError(error) && error.response?.status === 404) {
          setRequests({ phase: 'not-linked' })
          return
        }
        setRequests({ phase: 'error' })
      })
    return () => controller.abort()
  }, [version])

  const holidayDays = new Set(holidays.keys())
  const days = businessDaysBetween(values.start, values.end, holidayDays)
  const holidaysInRange = [...holidays.entries()].filter(
    ([day]) => values.start !== '' && values.end !== '' && values.start <= day && day <= values.end,
  )

  function change(field: keyof Values, value: string) {
    setValues((previous) => ({ ...previous, [field]: value }))
    setErrors((previous) => ({ ...previous, [field]: undefined }))
    setMessage(null)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = validate(values, days, balance)
    setErrors(found)
    if (Object.keys(found).length > 0) return

    setIsSending(true)
    try {
      const created = await createVacationRequest({ start_date: values.start, end_date: values.end })
      setValues({ start: '', end: '' })
      setMessage({
        kind: 'success',
        text: `Solicitud enviada por ${created.business_days} días hábiles. Queda pendiente de aprobación.`,
      })
      setVersion((count) => count + 1)
    } catch (error) {
      const result = serverErrors(error)
      setErrors(result.errors)
      if (result.message !== null) setMessage({ kind: 'error', text: result.message })
    } finally {
      setIsSending(false)
    }
  }

  async function handleCancel(request: VacationRequest) {
    setCancellingId(request.id)
    try {
      await cancelMyVacationRequest(request.id)
      setMessage({
        kind: 'success',
        text: `Solicitud del ${formatDate(request.start_date)} cancelada. Los días volvieron a tu saldo.`,
      })
      setVersion((count) => count + 1)
    } catch {
      setMessage({
        kind: 'error',
        text: 'No se pudo cancelar la solicitud. Puede que ya haya empezado o que Recursos Humanos la haya decidido.',
      })
      setVersion((count) => count + 1)
    } finally {
      setConfirmingId(null)
      setCancellingId(null)
    }
  }

  const today = todayInBogota()

  if (requests.phase === 'not-linked') {
    return (
      <div className="card empty-state">
        <IconCalendar size={32} />
        <h2>Tu cuenta no tiene un expediente</h2>
        <p className="muted">Pide a Recursos Humanos que la vincule con tu registro de empleado.</p>
      </div>
    )
  }

  const describedBy = (field: keyof Values) =>
    errors[field] !== undefined ? `vacation-${field}-error` : undefined

  return (
    <section>
      <header className="page-header">
        <h1 className="page-title">Mis vacaciones</h1>
      </header>

      <div className="detail-sections">
        <VacationBalanceCard employeeId={null} version={version} onLoaded={setBalance} />

        <form
          className="card detail-section"
          aria-labelledby="vacation-form-title"
          onSubmit={(event) => void handleSubmit(event)}
          noValidate
        >
          <h2 id="vacation-form-title" className="section-kicker">
            SOLICITAR VACACIONES
          </h2>

          {message !== null && (
            <div
              className={message.kind === 'error' ? 'alert alert-error' : 'alert alert-success'}
              role={message.kind === 'error' ? 'alert' : 'status'}
            >
              {message.kind === 'error' ? <IconAlert size={20} /> : <IconCheck size={20} />}
              <div className="alert-body">
                <span>{message.text}</span>
              </div>
            </div>
          )}

          <div className="form-grid">
            <div className={`field${errors.start !== undefined ? ' field-invalid' : ''}`}>
              <div className="field-label-row">
                <label htmlFor="vacation-start">Fecha de inicio</label>
              </div>
              <input
                id="vacation-start"
                type="date"
                min={todayInBogota()}
                value={values.start}
                onChange={(event) => change('start', event.target.value)}
                aria-invalid={errors.start !== undefined}
                aria-describedby={describedBy('start')}
              />
              {errors.start !== undefined && (
                <p className="field-error" id="vacation-start-error">
                  {errors.start}
                </p>
              )}
            </div>

            <div className={`field${errors.end !== undefined ? ' field-invalid' : ''}`}>
              <div className="field-label-row">
                <label htmlFor="vacation-end">Fecha de fin</label>
              </div>
              <input
                id="vacation-end"
                type="date"
                min={values.start !== '' ? values.start : todayInBogota()}
                value={values.end}
                onChange={(event) => change('end', event.target.value)}
                aria-invalid={errors.end !== undefined}
                aria-describedby={describedBy('end')}
              />
              {errors.end !== undefined && (
                <p className="field-error" id="vacation-end-error">
                  {errors.end}
                </p>
              )}
            </div>
          </div>

          {/* CA02: the count updates as the dates change; screen readers hear it too. */}
          <p className="balance-headline" aria-live="polite" id="vacation-business-days">
            {days === null ? (
              <span className="muted">Elige las dos fechas para ver los días hábiles.</span>
            ) : (
              <>
                Días hábiles solicitados: <strong>{days}</strong>
                <span className="muted"> (sin sábados, domingos ni festivos)</span>
                {holidaysInRange.length > 0 && (
                  <span className="field-help">
                    Festivos en el rango:{' '}
                    {holidaysInRange.map(([day, name]) => `${formatDate(day)} (${name})`).join(', ')}
                  </span>
                )}
              </>
            )}
          </p>

          <div className="form-actions">
            <button type="submit" className="btn btn-primary" disabled={isSending}>
              {isSending ? 'Enviando…' : 'Enviar solicitud'}
            </button>
          </div>
        </form>

        <section className="card detail-section" aria-labelledby="my-requests-title">
          <h2 id="my-requests-title" className="section-kicker">
            MIS SOLICITUDES
          </h2>
          {requests.phase === 'loading' && <p className="muted">Cargando solicitudes…</p>}
          {requests.phase === 'error' && (
            <p className="muted">No se pudieron cargar tus solicitudes.</p>
          )}
          {requests.phase === 'ready' && requests.requests.length === 0 && (
            <p className="muted">Aún no has solicitado vacaciones.</p>
          )}
          {requests.phase === 'ready' && requests.requests.length > 0 && (
            <div className="table-wrap">
              <table className="table" aria-label="Mis solicitudes de vacaciones">
                <thead>
                  <tr>
                    <th scope="col">Desde</th>
                    <th scope="col">Hasta</th>
                    <th scope="col">Días hábiles</th>
                    <th scope="col">Estado</th>
                    <th scope="col">Solicitada el</th>
                    <th scope="col">Motivo</th>
                    <th scope="col">Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {requests.requests.map((request) => (
                    <tr key={request.id}>
                      <td>{formatDate(request.start_date)}</td>
                      <td>{formatDate(request.end_date)}</td>
                      <td>{request.business_days}</td>
                      <td>
                        <span className={STATUS_BADGES[request.status]}>
                          {VACATION_STATUS_LABELS[request.status]}
                        </span>
                      </td>
                      <td>{instantFormatter.format(new Date(request.created_at))}</td>
                      <td>{request.reason ?? '—'}</td>
                      <td>
                        {canCancel(request, today) && confirmingId !== request.id && (
                          <button
                            type="button"
                            className="btn btn-secondary"
                            onClick={() => setConfirmingId(request.id)}
                            aria-label={`Cancelar solicitud del ${formatDate(request.start_date)}`}
                          >
                            Cancelar
                          </button>
                        )}
                        {confirmingId === request.id && (
                          <div className="row-actions" role="group" aria-label="Confirmar cancelación">
                            <span>¿Cancelar esta solicitud?</span>
                            <button
                              type="button"
                              className="btn btn-danger"
                              onClick={() => void handleCancel(request)}
                              disabled={cancellingId === request.id}
                            >
                              {cancellingId === request.id ? 'Cancelando…' : 'Sí, cancelar'}
                            </button>
                            <button
                              type="button"
                              className="btn btn-secondary"
                              onClick={() => setConfirmingId(null)}
                              disabled={cancellingId === request.id}
                            >
                              No
                            </button>
                          </div>
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
