import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import axios from 'axios'
import { getEmployee } from '../api/employees'
import { IconAlert, IconUsers } from '../components/Icons'
import { CONTRACT_TYPES, DOCUMENT_TYPES, type Employee } from '../types/employee'

const dateFormatter = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long', timeZone: 'UTC' })
const salaryFormatter = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 2,
})

/** "2026-01-15" -> "15 de enero de 2026". Parsed as UTC so the day never shifts with the time zone. */
function formatDate(isoDate: string): string {
  return dateFormatter.format(new Date(`${isoDate}T00:00:00Z`))
}

/** First letter of the first name plus first letter of the first last name. */
function getInitials(employee: Employee): string {
  const first = employee.first_names.trim().charAt(0)
  const last = employee.last_names.trim().charAt(0)
  return `${first}${last}`.toUpperCase()
}

type Load =
  | { phase: 'loading' }
  | { phase: 'not-found' }
  | { phase: 'error' }
  | { phase: 'ready'; employee: Employee }

function DetailItem({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="detail-item">
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

// HU-2.3: full record of one employee, grouped as personal and employment data.
export function EmployeeDetailPage() {
  const { employeeId } = useParams()
  const [load, setLoad] = useState<Load>({ phase: 'loading' })
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    if (employeeId === undefined) return
    const controller = new AbortController()
    setLoad({ phase: 'loading' })

    getEmployee(employeeId, controller.signal)
      .then((employee) => setLoad({ phase: 'ready', employee }))
      .catch((error: unknown) => {
        if (axios.isCancel(error)) return
        // 404 (no such employee) and 422 (malformed id) both mean "not a valid record".
        if (axios.isAxiosError(error) && [404, 422].includes(error.response?.status ?? 0)) {
          setLoad({ phase: 'not-found' })
          return
        }
        setLoad({ phase: 'error' })
      })

    return () => controller.abort()
  }, [employeeId, reloadCount])

  const employee = load.phase === 'ready' ? load.employee : null

  return (
    <section>
      <nav className="breadcrumb-nav" aria-label="Ruta">
        <Link to="/empleados">
          <IconUsers size={16} /> Empleados
        </Link>
        <span aria-hidden="true">›</span>
        <strong>{employee === null ? 'Expediente' : `${employee.first_names} ${employee.last_names}`}</strong>
      </nav>

      {load.phase === 'loading' && (
        <p className="table-status muted" role="status">
          Cargando expediente…
        </p>
      )}

      {load.phase === 'not-found' && (
        <div className="card empty-state">
          <IconUsers size={32} />
          <h2>No encontramos este empleado</h2>
          <p className="muted">
            El expediente no existe o fue eliminado. Vuelve al directorio para buscar otro.
          </p>
          <Link to="/empleados" className="btn btn-primary">
            Volver a empleados
          </Link>
        </div>
      )}

      {load.phase === 'error' && (
        <div className="alert alert-error" role="alert">
          <IconAlert size={20} />
          <div className="alert-body">
            <strong>No se pudo cargar el expediente.</strong>
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

      {employee !== null && (
        <>
          <div className="detail-header">
            <span className="avatar avatar-lg" aria-hidden="true">
              {getInitials(employee)}
            </span>
            <div className="detail-header-text">
              <div className="detail-title-row">
                <h1 className="page-title">
                  {employee.first_names} {employee.last_names}
                </h1>
                <span
                  className={
                    employee.status === 'ACTIVO' ? 'badge badge-success' : 'badge badge-muted'
                  }
                >
                  {employee.status === 'ACTIVO' ? 'Activo' : 'Inactivo'}
                </span>
              </div>
              <p className="page-subtitle">
                {employee.position} · {employee.area}
              </p>
            </div>
          </div>

          <div className="detail-sections">
            <div className="card detail-section">
              <p className="section-kicker">DATOS PERSONALES</p>
              <dl className="detail-grid">
                <DetailItem label="Nombres">{employee.first_names}</DetailItem>
                <DetailItem label="Apellidos">{employee.last_names}</DetailItem>
                <DetailItem label="Tipo de documento">
                  {DOCUMENT_TYPES[employee.document_type]}
                </DetailItem>
                <DetailItem label="Número de documento">{employee.document_number}</DetailItem>
                <DetailItem label="Correo electrónico">{employee.email}</DetailItem>
                <DetailItem label="Teléfono">{employee.phone ?? 'No registrado'}</DetailItem>
              </dl>
            </div>

            <div className="card detail-section">
              <p className="section-kicker">DATOS LABORALES</p>
              <dl className="detail-grid">
                <DetailItem label="Cargo">{employee.position}</DetailItem>
                <DetailItem label="Área">{employee.area}</DetailItem>
                <DetailItem label="Salario">{salaryFormatter.format(Number(employee.salary))}</DetailItem>
                <DetailItem label="Tipo de contrato">
                  {CONTRACT_TYPES[employee.contract_type]}
                </DetailItem>
                <DetailItem label="Fecha de inicio">{formatDate(employee.start_date)}</DetailItem>
                <DetailItem label="Fecha de finalización">
                  {employee.end_date === null ? 'Sin fecha de fin' : formatDate(employee.end_date)}
                </DetailItem>
              </dl>
            </div>
          </div>
        </>
      )}
    </section>
  )
}
