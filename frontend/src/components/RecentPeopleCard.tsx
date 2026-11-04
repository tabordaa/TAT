import { Link } from 'react-router'
import type { PersonSummary } from '../types/employee'

interface RecentPeopleCardProps {
  id: string
  title: string
  linkLabel: string
  people: PersonSummary[]
  emptyText: string
  footnote?: string
  /** Departures use a neutral avatar: grey instead of the brand blue. */
  muted?: boolean
}

const dateFormatter = new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium', timeZone: 'UTC' })

/** "2026-01-15" -> "15 ene 2026". Parsed as UTC so the day never shifts with the time zone. */
function formatDate(isoDate: string): string {
  return dateFormatter.format(new Date(`${isoDate}T00:00:00Z`))
}

function getInitials(person: PersonSummary): string {
  return `${person.first_names.charAt(0)}${person.last_names.charAt(0)}`.toUpperCase()
}

export function RecentPeopleCard({
  id,
  title,
  linkLabel,
  people,
  emptyText,
  footnote,
  muted = false,
}: RecentPeopleCardProps) {
  return (
    <section className="card" aria-labelledby={id}>
      <div className="recent-header">
        <h2 id={id}>{title}</h2>
        <Link to="/empleados">{linkLabel}</Link>
      </div>

      {people.length === 0 ? (
        <p className="muted">{emptyText}</p>
      ) : (
        <ul>
          {people.map((person) => (
            <li key={person.id} className="recent-row">
              <span className={muted ? 'avatar avatar-muted' : 'avatar'} aria-hidden="true">
                {getInitials(person)}
              </span>
              <div className="recent-text">
                <Link to={`/empleados/${person.id}`} className="recent-name">
                  {person.first_names} {person.last_names}
                </Link>
                <span className="muted recent-meta">
                  {person.position} · {person.area}
                </span>
              </div>
              <span className="muted recent-date">
                {person.event_date === null ? 'Sin fecha' : formatDate(person.event_date)}
              </span>
            </li>
          ))}
        </ul>
      )}

      {footnote !== undefined && <p className="muted chart-footnote">{footnote}</p>}
    </section>
  )
}
