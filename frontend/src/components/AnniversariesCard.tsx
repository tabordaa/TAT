import { Link } from 'react-router'
import type { Anniversary } from '../types/employee'
import { todayInBogota } from '../utils/businessDays'
import { PersonAvatar } from './PersonAvatar'

interface AnniversariesCardProps {
  id: string
  anniversaries: Anniversary[]
}

const monthFormatter = new Intl.DateTimeFormat('es-CO', {
  month: 'long',
  timeZone: 'UTC',
})

const dayFormatter = new Intl.DateTimeFormat('es-CO', {
  day: 'numeric',
  month: 'short',
  timeZone: 'UTC',
})

function formatMonthName(isoDate: string): string {
  return monthFormatter.format(new Date(`${isoDate}T00:00:00Z`)).toLowerCase()
}

/** "2026-11-18" -> "18 nov". Parsed as UTC so the day never shifts with the time zone. */
function formatDay(isoDate: string): string {
  return dayFormatter.format(new Date(`${isoDate}T00:00:00Z`)).replace(/\.$/, '')
}

function getInitials(person: Anniversary): string {
  return `${person.first_names.trim().charAt(0)}${person.last_names.trim().charAt(0)}`.toUpperCase()
}

function yearsLabel(years: number): string {
  return years === 1 ? '1 año' : `${years} años`
}

export function AnniversariesCard({ id, anniversaries }: AnniversariesCardProps) {
  const todayIso = todayInBogota()
  // Prefer the month returned by the API so the heading always matches the listed dates.
  const monthName = formatMonthName(anniversaries[0]?.anniversary ?? todayIso)

  return (
    <section className="card anniversaries-card" aria-labelledby={id}>
      <div className="recent-header">
        <h2 id={id}>Aniversarios de {monthName}</h2>
      </div>

      {anniversaries.length === 0 ? (
        <p className="muted">Nadie cumple años en la empresa este mes.</p>
      ) : (
        <ul className="recent-list anniversary-list">
          {anniversaries.map((person) => {
            const isToday = person.anniversary === todayIso
            const fullName = `${person.first_names} ${person.last_names}`
            return (
              <li
                key={person.id}
                className={
                  isToday ? 'recent-row anniversary-row anniversary-today' : 'recent-row anniversary-row'
                }
              >
                <PersonAvatar
                  id={person.id}
                  name={fullName}
                  initials={getInitials(person)}
                  hasPhoto={person.has_photo}
                  size="sm"
                />
                <div className="recent-text">
                  <Link to={`/empleados/${person.id}`} className="recent-name">
                    {fullName}
                  </Link>
                  <span className="muted recent-meta">
                    {person.position} · {person.area}
                  </span>
                </div>
                <div className="anniversary-aside">
                  <span className="badge anniversary-years">{yearsLabel(person.years)}</span>
                  {isToday ? (
                    <span className="badge anniversary-today-badge">¡Hoy!</span>
                  ) : (
                    <span className="muted recent-date">{formatDay(person.anniversary)}</span>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
