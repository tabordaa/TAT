import { useEffect, useState } from 'react'
import axios from 'axios'
import { getSalaryHistory } from '../api/employees'
import type { SalaryChange } from '../types/employee'

const moneyFormatter = new Intl.NumberFormat('es-CO', {
  style: 'currency',
  currency: 'COP',
  maximumFractionDigits: 2,
})

// A change is an instant: shown in Colombia's time, whatever the viewer's clock says.
const dateTimeFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
  timeZone: 'America/Bogota',
})

type Load =
  | { phase: 'loading' }
  | { phase: 'error' }
  | { phase: 'ready'; changes: SalaryChange[] }

interface SalaryHistorySectionProps {
  employeeId: string
  /** The current salary: when it changes, the history is fetched again. */
  salary: string
}

// HU-2.5: every salary change of the employee, newest first. The API lets ADMIN,
// HR and MANAGER read it (the same people who see the current salary).
export function SalaryHistorySection({ employeeId, salary }: SalaryHistorySectionProps) {
  const [load, setLoad] = useState<Load>({ phase: 'loading' })

  useEffect(() => {
    const controller = new AbortController()
    setLoad({ phase: 'loading' })
    getSalaryHistory(employeeId, controller.signal)
      .then((changes) => setLoad({ phase: 'ready', changes }))
      .catch((error: unknown) => {
        if (!axios.isCancel(error)) setLoad({ phase: 'error' })
      })
    return () => controller.abort()
  }, [employeeId, salary])

  return (
    <section className="card detail-section" aria-labelledby="salary-history-title">
      <h2 id="salary-history-title" className="section-kicker">
        HISTORIAL SALARIAL
      </h2>

      {load.phase === 'loading' && (
        <p className="muted" role="status">
          Cargando historial…
        </p>
      )}
      {load.phase === 'error' && <p className="muted">No se pudo cargar el historial salarial.</p>}
      {load.phase === 'ready' && load.changes.length === 0 && (
        <p className="muted">Aún no hay cambios de salario registrados.</p>
      )}

      {load.phase === 'ready' && load.changes.length > 0 && (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Fecha del cambio</th>
                <th scope="col">Salario anterior</th>
                <th scope="col">Salario nuevo</th>
                <th scope="col">Responsable</th>
              </tr>
            </thead>
            <tbody>
              {load.changes.map((change) => (
                <tr key={change.id}>
                  <td>{dateTimeFormatter.format(new Date(change.changed_at))}</td>
                  <td>{moneyFormatter.format(Number(change.old_salary))}</td>
                  <td>
                    <span className="cell-strong">{moneyFormatter.format(Number(change.new_salary))}</span>
                  </td>
                  <td>{change.changed_by_name}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
