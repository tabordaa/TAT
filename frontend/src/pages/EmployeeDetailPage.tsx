import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import axios from 'axios'
import { getEmployee } from '../api/employees'
import { useAuth } from '../auth/useAuth'
import {
  EmployeeRecordHeader,
  EmploymentDataSection,
  PersonalDataSection,
} from '../components/EmployeeRecord'
import { IconAlert, IconUsers } from '../components/Icons'
import { ResetPasswordCard } from '../components/ResetPasswordCard'
import type { EmployeeDetail } from '../types/employee'

type Load =
  | { phase: 'loading' }
  | { phase: 'not-found' }
  | { phase: 'error' }
  | { phase: 'ready'; employee: EmployeeDetail }

// HU-2.3: full record of one employee, grouped as personal and employment data.
export function EmployeeDetailPage() {
  const { employeeId } = useParams()
  const { user } = useAuth()
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
          <EmployeeRecordHeader employee={employee} />

          <div className="detail-sections">
            <PersonalDataSection employee={employee} />
            <EmploymentDataSection employee={employee} />

            {user?.role === 'ADMIN' && employee.has_account && (
              <ResetPasswordCard employee={employee} />
            )}
          </div>
        </>
      )}
    </section>
  )
}
