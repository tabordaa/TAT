import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import axios from 'axios'
import {
  approveVacationRequest,
  getVacationInbox,
  rejectVacationRequest,
} from '../api/vacations'
import { IconAlert, IconCalendar, IconCheck } from '../components/Icons'
import type { VacationInboxItem } from '../types/vacation'

// Same limits as the API (VacationReject).
const REASON_MIN = 5
const REASON_MAX = 500

const dateFormatter = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeZone: 'UTC' })
const instantFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeZone: 'America/Bogota',
})
const daysFormatter = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 })

function formatDate(value: string): string {
  return dateFormatter.format(new Date(`${value}T00:00:00Z`))
}

/** The API answers {field, message}; each case gets a message in Spanish. */
function toMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status
    const detail: unknown = error.response?.data?.detail
    const field =
      typeof detail === 'object' && detail !== null && 'field' in detail ? String(detail.field) : ''
    if (status === 409 && field === 'business_days')
      return 'El empleado ya no tiene días suficientes para esta solicitud.'
    if (status === 409) return 'La solicitud ya fue decidida o el empleado ya no está activo.'
    if (status === 403 && field === 'employee') return 'No puedes decidir sobre tu propia solicitud.'
    if (status === 403) return 'No tienes permiso para realizar esta acción.'
    if (status === 404) return 'La solicitud ya no existe.'
    if (status === 422) return `El motivo debe tener entre ${REASON_MIN} y ${REASON_MAX} caracteres.`
  }
  return 'No se pudo guardar la decisión. Inténtalo de nuevo.'
}

type Load =
  | { phase: 'loading' }
  | { phase: 'error' }
  | { phase: 'ready'; items: VacationInboxItem[] }

interface RejectModalProps {
  item: VacationInboxItem
  onCancel: () => void
  onDone: (item: VacationInboxItem) => void
}

// HU-4.2 CA03: rejecting asks for a reason, which the employee will read.
function RejectModal({ item, onCancel, onDone }: RejectModalProps) {
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onCancel()
    }
    document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [onCancel])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const trimmed = reason.trim()
    if (trimmed.length < REASON_MIN) {
      setError(`Escribe el motivo del rechazo (mínimo ${REASON_MIN} caracteres).`)
      return
    }
    setIsSaving(true)
    setError(null)
    try {
      onDone(await rejectVacationRequest(item.id, trimmed))
    } catch (err) {
      setError(toMessage(err))
      setIsSaving(false)
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="card modal" role="dialog" aria-modal="true" aria-labelledby="reject-title">
        <h2 id="reject-title">Rechazar vacaciones de {item.employee_name}</h2>
        <p className="muted">
          Del {formatDate(item.start_date)} al {formatDate(item.end_date)} ({item.business_days} días
          hábiles). El empleado verá este motivo.
        </p>

        <form onSubmit={(event) => void handleSubmit(event)} noValidate>
          <div className={`field${error !== null ? ' field-invalid' : ''}`}>
            <div className="field-label-row">
              <label htmlFor="reject-reason">Motivo del rechazo</label>
            </div>
            <textarea
              id="reject-reason"
              rows={4}
              autoFocus
              maxLength={REASON_MAX}
              value={reason}
              onChange={(event) => {
                setReason(event.target.value)
                setError(null)
              }}
              aria-invalid={error !== null}
              aria-describedby={error !== null ? 'reject-reason-error' : undefined}
            />
            {error !== null && (
              <p className="field-error" id="reject-reason-error">
                {error}
              </p>
            )}
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={isSaving}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={isSaving}>
              {isSaving ? 'Guardando…' : 'Rechazar solicitud'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// HU-4.2: HR's inbox of pending requests (CA01), with approve (CA02) and reject (CA03).
// Only ADMIN and HR reach this page (RoleRoute); the API checks the same.
export function VacationInboxPage() {
  const [load, setLoad] = useState<Load>({ phase: 'loading' })
  const [reloadCount, setReloadCount] = useState(0)
  const [rejecting, setRejecting] = useState<VacationInboxItem | null>(null)
  const [busyId, setBusyId] = useState<string | null>(null)
  const [message, setMessage] = useState<{ kind: 'error' | 'success'; text: string } | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoad({ phase: 'loading' })
    getVacationInbox('PENDIENTE', controller.signal)
      .then((items) => setLoad({ phase: 'ready', items }))
      .catch((error: unknown) => {
        if (!axios.isCancel(error)) setLoad({ phase: 'error' })
      })
    return () => controller.abort()
  }, [reloadCount])

  function decided(item: VacationInboxItem, verb: string) {
    setMessage({ kind: 'success', text: `Solicitud de ${item.employee_name} ${verb}.` })
    setReloadCount((count) => count + 1)
  }

  async function approve(item: VacationInboxItem) {
    setBusyId(item.id)
    setMessage(null)
    try {
      decided(await approveVacationRequest(item.id), 'aprobada')
    } catch (error) {
      setMessage({ kind: 'error', text: toMessage(error) })
      setReloadCount((count) => count + 1)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section>
      <header className="page-header">
        <h1 className="page-title">Solicitudes de vacaciones</h1>
      </header>

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

      <div className="card">
        {load.phase === 'loading' && <p className="table-status muted">Cargando solicitudes…</p>}
        {load.phase === 'error' && (
          <div className="alert alert-error" role="alert">
            <IconAlert size={20} />
            <div className="alert-body">
              <strong>No se pudieron cargar las solicitudes.</strong>
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
        {load.phase === 'ready' && load.items.length === 0 && (
          <div className="empty-state">
            <IconCalendar size={32} />
            <h2>No hay solicitudes pendientes</h2>
            <p className="muted">Cuando un empleado solicite vacaciones aparecerá aquí.</p>
          </div>
        )}
        {load.phase === 'ready' && load.items.length > 0 && (
          <div className="table-wrap">
            <table className="table" aria-label="Solicitudes pendientes">
              <thead>
                <tr>
                  <th scope="col">Empleado</th>
                  <th scope="col">Desde</th>
                  <th scope="col">Hasta</th>
                  <th scope="col">Días hábiles</th>
                  <th scope="col">Disponibles</th>
                  <th scope="col">Solicitada el</th>
                  <th scope="col">Acciones</th>
                </tr>
              </thead>
              <tbody>
                {load.items.map((item) => {
                  const exceeds = item.business_days > Number(item.available_days)
                  return (
                    <tr key={item.id}>
                      <td>
                        <Link to={`/empleados/${encodeURIComponent(item.employee_id)}`}>
                          {item.employee_name}
                        </Link>
                      </td>
                      <td>{formatDate(item.start_date)}</td>
                      <td>{formatDate(item.end_date)}</td>
                      <td className="cell-strong">{item.business_days}</td>
                      <td>
                        {daysFormatter.format(Number(item.available_days))}
                        {exceeds && <span className="badge badge-danger"> Insuficiente</span>}
                      </td>
                      <td>{instantFormatter.format(new Date(item.created_at))}</td>
                      <td>
                        <div className="row-actions">
                          <button
                            type="button"
                            className="btn btn-primary"
                            disabled={busyId !== null || exceeds}
                            aria-label={`Aprobar solicitud de ${item.employee_name}`}
                            onClick={() => void approve(item)}
                          >
                            Aprobar
                          </button>
                          <button
                            type="button"
                            className="btn btn-secondary"
                            disabled={busyId !== null}
                            aria-label={`Rechazar solicitud de ${item.employee_name}`}
                            onClick={() => {
                              setMessage(null)
                              setRejecting(item)
                            }}
                          >
                            Rechazar
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {rejecting !== null && (
        <RejectModal
          item={rejecting}
          onCancel={() => setRejecting(null)}
          onDone={(item) => {
            setRejecting(null)
            decided(item, 'rechazada')
          }}
        />
      )}
    </section>
  )
}
