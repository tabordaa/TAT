import { useEffect, useState, type ChangeEvent } from 'react'
import { Link, useLocation } from 'react-router'
import axios from 'axios'
import { listEmployees } from '../api/employees'
import {
  IconAlert,
  IconCheck,
  IconClose,
  IconSearch,
  IconUserPlus,
  IconUsers,
} from '../components/Icons'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import type { EmployeeListResponse, EmployeeStatus } from '../types/employee'

const PAGE_SIZE = 10
// Wait for a short pause in typing before asking the API (HU-2.2 CA02).
const SEARCH_DEBOUNCE_MS = 300
const MAX_SEARCH_LENGTH = 100 // same limit as the API

const STATUS_LABELS: Record<EmployeeStatus, string> = {
  ACTIVO: 'Activo',
  INACTIVO: 'Inactivo',
}

const dateFormatter = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeZone: 'UTC' })

/** "2026-01-15" -> "15 ene 2026". Parsed as UTC so the day never shifts with the time zone. */
function formatDate(isoDate: string): string {
  return dateFormatter.format(new Date(`${isoDate}T00:00:00Z`))
}

/** Reads the name sent by RegisterEmployeePage after a successful save. */
function getCreatedName(state: unknown): string | null {
  if (typeof state === 'object' && state !== null && 'createdName' in state) {
    const { createdName } = state
    return typeof createdName === 'string' ? createdName : null
  }
  return null
}

type StatusFilter = EmployeeStatus | ''

function isStatusFilter(value: string): value is StatusFilter {
  return value === '' || value === 'ACTIVO' || value === 'INACTIVO'
}

type Load =
  | { phase: 'loading' }
  | { phase: 'error' }
  | { phase: 'ready'; data: EmployeeListResponse }

// HU-2.2: directory with search, status filter and pagination.
export function EmployeesPage() {
  const createdName = getCreatedName(useLocation().state)

  // searchText follows every keystroke (so the input feels instant); appliedQ is
  // what the API is actually asked, updated only after the debounce.
  const [searchText, setSearchText] = useState('')
  const [appliedQ, setAppliedQ] = useState('')
  const [status, setStatus] = useState<StatusFilter>('')
  const [page, setPage] = useState(1)
  const [load, setLoad] = useState<Load>({ phase: 'loading' })
  const [reloadCount, setReloadCount] = useState(0)
  const debouncedText = useDebouncedValue(searchText, SEARCH_DEBOUNCE_MS)

  useEffect(() => {
    // Both updates are batched into one render, so a new search triggers a
    // single request, always starting from the first page.
    setAppliedQ(debouncedText.trim())
    setPage(1)
  }, [debouncedText])

  useEffect(() => {
    // One request per change; the cleanup cancels a stale one so a slow answer
    // can never overwrite a newer result.
    const controller = new AbortController()
    setLoad({ phase: 'loading' })

    listEmployees({ q: appliedQ, status, page, size: PAGE_SIZE }, controller.signal)
      .then((data) => setLoad({ phase: 'ready', data }))
      .catch((error: unknown) => {
        if (axios.isCancel(error)) return
        setLoad({ phase: 'error' })
      })

    return () => controller.abort()
  }, [appliedQ, status, page, reloadCount])

  function handleStatusChange(event: ChangeEvent<HTMLSelectElement>) {
    const value = event.target.value
    if (isStatusFilter(value)) {
      setStatus(value)
      setPage(1) // a new filter always starts at the first page
    }
  }

  const data = load.phase === 'ready' ? load.data : null
  const totalPages = data === null ? 1 : Math.max(1, Math.ceil(data.total / data.size))
  const isFiltered = status !== '' || appliedQ !== ''

  return (
    <section>
      <div className="page-header">
        <div>
          <p className="breadcrumb">GESTIÓN HUMANA · Directorio central</p>
          <h1 className="page-title">Empleados</h1>
          <p className="page-subtitle">Gestión de contratos y cargos de la organización</p>
        </div>
        <Link to="/empleados/nuevo" className="btn btn-primary">
          <IconUserPlus /> Registrar empleado
        </Link>
      </div>

      {createdName !== null && (
        <div className="alert alert-success" role="status">
          <IconCheck size={20} />
          <div className="alert-body">
            <strong>Empleado registrado.</strong>
            <span>{createdName} quedó registrado con estado ACTIVO.</span>
          </div>
        </div>
      )}

      <div className="card table-card">
        <div className="toolbar">
          <div className="field toolbar-search" role="search">
            <div className="field-label-row">
              <label htmlFor="employee-search">Buscar</label>
            </div>
            <div className="search-box">
              <IconSearch size={16} />
              <input
                id="employee-search"
                type="search"
                value={searchText}
                maxLength={MAX_SEARCH_LENGTH}
                placeholder="Nombre o número de documento"
                autoComplete="off"
                onChange={(event) => setSearchText(event.target.value)}
              />
              {searchText !== '' && (
                <button
                  type="button"
                  className="search-clear"
                  aria-label="Borrar búsqueda"
                  onClick={() => setSearchText('')}
                >
                  <IconClose size={14} />
                </button>
              )}
            </div>
          </div>
          <div className="field toolbar-field">
            <div className="field-label-row">
              <label htmlFor="status-filter">Estado</label>
            </div>
            <select id="status-filter" value={status} onChange={handleStatusChange}>
              <option value="">Todos</option>
              <option value="ACTIVO">Activos</option>
              <option value="INACTIVO">Inactivos</option>
            </select>
          </div>
          <p className="toolbar-count muted" aria-live="polite">
            {data !== null && `${data.total} ${data.total === 1 ? 'empleado' : 'empleados'}`}
          </p>
        </div>

        {load.phase === 'error' && (
          <div className="alert alert-error" role="alert">
            <IconAlert size={20} />
            <div className="alert-body">
              <strong>No se pudo cargar el listado.</strong>
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
            Cargando empleados…
          </p>
        )}

        {data !== null && data.items.length === 0 && (
          <div className="empty-state">
            <IconUsers size={32} />
            <h2>{isFiltered ? 'Sin resultados' : 'Aún no hay empleados'}</h2>
            <p className="muted">
              {isFiltered
                ? 'Ningún empleado coincide con la búsqueda o el filtro seleccionado.'
                : 'Registra el primer empleado para verlo aquí.'}
            </p>
          </div>
        )}

        {data !== null && data.items.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Empleado</th>
                  <th scope="col">Documento</th>
                  <th scope="col">Cargo</th>
                  <th scope="col">Inicio</th>
                  <th scope="col">Estado</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((employee) => (
                  <tr key={employee.id}>
                    <td>
                      <span className="cell-strong">
                        {employee.first_names} {employee.last_names}
                      </span>
                      <span className="cell-sub">{employee.area}</span>
                    </td>
                    <td>
                      {employee.document_type} {employee.document_number}
                    </td>
                    <td>{employee.position}</td>
                    <td>{formatDate(employee.start_date)}</td>
                    <td>
                      <span
                        className={
                          employee.status === 'ACTIVO' ? 'badge badge-success' : 'badge badge-muted'
                        }
                      >
                        {STATUS_LABELS[employee.status]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data !== null && data.total > 0 && (
          <nav className="pagination" aria-label="Paginación del listado">
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
