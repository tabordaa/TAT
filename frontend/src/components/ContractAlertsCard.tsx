import { Link } from 'react-router'
import type { ContractAlert } from '../types/employee'

function daysLabel(daysLeft: number): string {
  if (daysLeft < 0) {
    const days = Math.abs(daysLeft)
    return `Venció hace ${days} ${days === 1 ? 'día' : 'días'}`
  }
  if (daysLeft === 0) return 'Vence hoy'
  return `${daysLeft} ${daysLeft === 1 ? 'día' : 'días'}`
}

// HU-3.2 (merged with HU-6.2): active employees whose contract ends in under 30 days.
export function ContractAlertsCard({ alerts }: { alerts: ContractAlert[] }) {
  return (
    <section className="card contract-alerts" aria-labelledby="contract-alerts-title">
      <div className="recent-header">
        <h2 id="contract-alerts-title">Contratos por vencer</h2>
      </div>

      {alerts.length === 0 ? (
        <p className="muted">Ningún contrato vence en los próximos 30 días.</p>
      ) : (
        <div className="table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Empleado</th>
                <th scope="col">Días restantes</th>
                <th scope="col">Estado</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((alert) => (
                <tr key={alert.id}>
                  <td>
                    <Link to={`/empleados/${alert.id}`} className="cell-link">
                      <span className="cell-strong">
                        {alert.first_names} {alert.last_names}
                      </span>
                    </Link>
                    <span className="cell-sub">{alert.position}</span>
                  </td>
                  <td>{daysLabel(alert.days_left)}</td>
                  <td>
                    <span
                      className={
                        alert.state === 'VENCIDO' ? 'badge badge-danger' : 'badge badge-warning'
                      }
                    >
                      {alert.state === 'VENCIDO' ? 'Vencido' : 'Por vencer'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
