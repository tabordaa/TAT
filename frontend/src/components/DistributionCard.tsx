import type { CountItem } from '../types/employee'

interface DistributionCardProps {
  id: string
  title: string
  subtitle: string
  items: CountItem[]
  /** Percentages are taken over this total, so every card agrees with the headline number. */
  total: number
}

/** Horizontal bars, biggest first. Plain HTML/CSS: the numbers are printed, so no chart library. */
export function DistributionCard({ id, title, subtitle, items, total }: DistributionCardProps) {
  const max = Math.max(1, ...items.map((item) => item.count))

  return (
    <section className="card" aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      <p className="muted chart-subtitle">{subtitle}</p>

      {items.length === 0 ? (
        <p className="muted">Todavía no hay empleados activos para mostrar.</p>
      ) : (
        <ul className="bar-list">
          {items.map((item) => {
            const share = total > 0 ? Math.round((item.count / total) * 100) : 0
            return (
              <li
                key={item.name}
                className="bar-row"
                title={`${item.name}: ${item.count} empleados (${share}%)`}
              >
                <span className="bar-name">{item.name}</span>
                <div className="bar-track" aria-hidden="true">
                  <div className="bar-fill" style={{ width: `${(item.count / max) * 100}%` }} />
                </div>
                <span className="bar-value">
                  <strong>{item.count}</strong> <span className="muted">{share}%</span>
                </span>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
