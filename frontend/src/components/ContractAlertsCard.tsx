import { Link } from 'react-router'
import type { ContractAlert } from '../types/employee'
import { PersonAvatar } from './PersonAvatar'

function getInitials(alert: ContractAlert): string {
  return `${alert.first_names.trim().charAt(0)}${alert.last_names.trim().charAt(0)}`.toUpperCase()
}

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
    <section className="card table-card contract-alerts" aria-labelledby="contract-alerts-title">
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
              {alerts.map((alert) => {
                const fullName = `${alert.first_names} ${alert.last_names}`
                return (
                  <tr key={alert.id}>
                    <td>
                      <div className="employee-cell employee-cell-compact">
                        {/* ContractAlert does not include has_photo; render deterministic initials without 404 requests. */}
                        <PersonAvatar
                          id={alert.id}
                          name={fullName}
                          initials={getInitials(alert)}
                          hasPhoto={false}
                          size="xs"
                        />
                        <div className="employee-cell-text">
                          <Link to={`/empleados/${alert.id}`} className="cell-link">
                            <span className="cell-strong">{fullName}</span>
                          </Link>
                          <span className="cell-sub">{alert.position}</span>
                        </div>
                      </div>
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
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
