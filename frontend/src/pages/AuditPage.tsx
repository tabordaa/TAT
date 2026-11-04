import { useEffect, useState } from 'react'
import axios from 'axios'
import { listAuditLogs } from '../api/audit'
import { IconAlert, IconShield } from '../components/Icons'
import type { AuditLogItem, AuditLogListResponse } from '../types/audit'

const PAGE_SIZE = 20

const ACTION_LABELS: Record<string, string> = {
  EMPLOYEE_CREATED: 'Empleado registrado',
  ACCOUNT_CREATED: 'Cuenta creada',
  PASSWORD_CHANGED: 'Contraseña cambiada',
  PASSWORD_RESET: 'Contraseña restablecida',
  CONTACT_UPDATED: 'Datos de contacto actualizados',
  PHOTO_UPDATED: 'Foto actualizada',
  CONTRACT_ASSIGNED: 'Contrato asignado',
  EMPLOYEE_REHIRED: 'Reingreso',
  CONTRACT_TERMINATED: 'Contrato finalizado',
}

const FIELD_LABELS: Record<string, string> = {
  status: 'Estado',
  position: 'Cargo',
  area: 'Área',
  salary: 'Salario',
  contract_type: 'Tipo de contrato',
  start_date: 'Inicio',
  end_date: 'Fin',
  email: 'Correo',
  role: 'Rol',
  phone: 'Teléfono',
  address: 'Dirección',
  is_active: 'Cuenta activa',
  must_change_password: 'Requiere cambio de contraseña',
  photo: 'Foto',
}

const dateTimeFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
})

function ChangeList({ item }: { item: AuditLogItem }) {
  const entries = Object.entries(item.changes)
  if (entries.length === 0) {
    return <span className="muted">Sin detalle</span>
  }
  return (
    <ul className="audit-changes">
      {entries.map(([field, change]) => (
        <li key={field}>
          <strong>{FIELD_LABELS[field] ?? field}:</strong> {change.old ?? '—'} → {change.new ?? '—'}
        </li>
      ))}
    </ul>
  )
}

type Load =
  | { phase: 'loading' }
  | { phase: 'error' }
  | { phase: 'ready'; data: AuditLogListResponse }

// HU-5.1 CA02: the audit trail, ordered by date, exclusive to the Admin.
export function AuditPage() {
  const [page, setPage] = useState(1)
  const [load, setLoad] = useState<Load>({ phase: 'loading' })
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoad({ phase: 'loading' })

    listAuditLogs(page, PAGE_SIZE, controller.signal)
      .then((data) => setLoad({ phase: 'ready', data }))
      .catch((error: unknown) => {
        if (axios.isCancel(error)) return
        setLoad({ phase: 'error' })
      })

    return () => controller.abort()
  }, [page, reloadCount])

  const data = load.phase === 'ready' ? load.data : null
  const totalPages = data === null ? 1 : Math.max(1, Math.ceil(data.total / data.size))

  return (
    <section>
      <div className="page-header">
        <div>
          <p className="breadcrumb">ADMINISTRACIÓN · Seguridad</p>
          <h1 className="page-title">Auditoría</h1>
          <p className="page-subtitle">Quién cambió datos críticos, cuándo y desde dónde</p>
        </div>
      </div>

      <div className="card table-card">
        {load.phase === 'error' && (
          <div className="alert alert-error" role="alert">
            <IconAlert size={20} />
            <div className="alert-body">
              <strong>No se pudo cargar el historial.</strong>
              <span>Revisa tu conexión e inténtalo de nuevo.</span>
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

        {load.phase === 'loading' && (
          <p className="table-status muted" role="status">
            Cargando historial…
          </p>
        )}

        {data !== null && data.items.length === 0 && (
          <div className="empty-state">
            <IconShield size={32} />
            <h2>Aún no hay registros</h2>
            <p className="muted">Los cambios en datos críticos aparecerán aquí.</p>
          </div>
        )}

        {data !== null && data.items.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Fecha</th>
                  <th scope="col">Usuario</th>
                  <th scope="col">Acción</th>
                  <th scope="col">Cambios</th>
                  <th scope="col">IP</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>{dateTimeFormatter.format(new Date(item.created_at))}</td>
                    <td>{item.actor_email}</td>
                    <td>{ACTION_LABELS[item.action] ?? item.action}</td>
                    <td>
                      <ChangeList item={item} />
                    </td>
                    <td>{item.ip}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data !== null && data.total > 0 && (
          <nav className="pagination" aria-label="Paginación del historial">
            <span className="muted">
              Página {data.page} de {totalPages}
            </span>
            <div className="pagination-actions">
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setPage((current) => current - 1)}
                disabled={data.page <= 1}
              >
                Anterior
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setPage((current) => current + 1)}
                disabled={data.page >= totalPages}
              >
                Siguiente
              </button>
            </div>
          </nav>
        )}
      </div>
    </section>
  )
}
