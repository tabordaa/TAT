import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import axios from 'axios'
import { getEmployeeOverview, getEmployeeStats } from '../api/employees'
import { useAuth } from '../auth/useAuth'
import { DistributionCard } from '../components/DistributionCard'
import { IconAlert, IconCheck, IconUser, IconUsers } from '../components/Icons'
import { RecentPeopleCard } from '../components/RecentPeopleCard'
import type { EmployeeOverview, EmployeeStats } from '../types/employee'

// Numbers are re-read while the dashboard is open, so they follow the database
// without reloading the page (HU-6.1 CA02).
const REFRESH_INTERVAL_MS = 30_000

const numberFormatter = new Intl.NumberFormat('es-CO')

type Load =
  | { phase: 'loading' }
  | { phase: 'forbidden' }
  | { phase: 'error' }
  | { phase: 'ready'; stats: EmployeeStats; overview: EmployeeOverview }

interface StatCardProps {
  label: string
  value: number | null
  icon: ReactNode
  tone: 'neutral' | 'success' | 'muted'
}

function StatCard({ label, value, icon, tone }: StatCardProps) {
  return (
    <article className={`card stat-card stat-${tone}`}>
      <span className="stat-icon" aria-hidden="true">
        {icon}
      </span>
      <div>
        <p className="stat-label">{label}</p>
        <p className="stat-value">{value === null ? '—' : numberFormatter.format(value)}</p>
      </div>
    </article>
  )
}

export function DashboardPage() {
  const { user } = useAuth()
  const [load, setLoad] = useState<Load>({ phase: 'loading' })
  const [reloadCount, setReloadCount] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    function refresh() {
      // Both requests together: the cards and the charts always show the same moment.
      Promise.all([getEmployeeStats(controller.signal), getEmployeeOverview(controller.signal)])
        .then(([stats, overview]) => setLoad({ phase: 'ready', stats, overview }))
        .catch((error: unknown) => {
          if (axios.isCancel(error)) return
          if (axios.isAxiosError(error) && error.response?.status === 403) {
            setLoad({ phase: 'forbidden' }) // this role has no access to the numbers
            return
          }
          // Keep showing the last good numbers if a background refresh fails.
          setLoad((current) => (current.phase === 'ready' ? current : { phase: 'error' }))
        })
    }

    refresh()
    const timer = setInterval(refresh, REFRESH_INTERVAL_MS)
    // Coming back to the tab: refresh right away instead of waiting for the next tick.
    function handleVisibility() {
      if (document.visibilityState === 'visible') refresh()
    }
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      controller.abort()
      clearInterval(timer)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [reloadCount])

  const stats = load.phase === 'ready' ? load.stats : null

  return (
    <section>
      <p className="breadcrumb">GESTIÓN HUMANA</p>
      <h1 className="page-title">Hola, {user?.full_name}</h1>
      <p className="page-subtitle">Panel principal de TAT</p>

      {load.phase === 'error' && (
        <div className="alert alert-error stat-alert" role="alert">
          <IconAlert size={20} />
          <div className="alert-body">
            <strong>No se pudieron cargar los indicadores.</strong>
            <span>Revisa tu conexión e inténtalo de nuevo.</span>
          </div>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => {
              setLoad({ phase: 'loading' })
              setReloadCount((count) => count + 1)
            }}
          >
            Reintentar
          </button>
        </div>
      )}

      {load.phase === 'forbidden' ? (
        <div className="card empty-state">
          <IconUsers size={32} />
          <h2>Indicadores no disponibles</h2>
          <p className="muted">Tu rol no tiene acceso a los indicadores de empleados.</p>
        </div>
      ) : (
        <>
          <div className="stat-grid" aria-busy={load.phase === 'loading'}>
            <StatCard
              label="Total de empleados históricos"
              value={stats?.total ?? null}
              icon={<IconUsers size={22} />}
              tone="neutral"
            />
            <StatCard
              label="Empleados activos"
              value={stats?.active ?? null}
              icon={<IconCheck size={22} />}
              tone="success"
            />
            <StatCard
              label="Empleados inactivos"
              value={stats?.inactive ?? null}
              icon={<IconUser size={22} />}
              tone="muted"
            />
          </div>

          {load.phase === 'ready' && (
            <div className="chart-grid">
              <DistributionCard
                id="chart-area"
                title="Empleados por área"
                subtitle="Solo empleados activos, de mayor a menor"
                items={load.overview.by_area}
                total={load.stats.active}
              />
              <DistributionCard
                id="chart-position"
                title="Empleados por cargo"
                subtitle="Solo empleados activos; los cargos con menos personas se agrupan en «Otros»"
                items={load.overview.by_position}
                total={load.stats.active}
              />
              <RecentPeopleCard
                id="recent-hires"
                title="Ingresos recientes"
                linkLabel="Ver todos"
                people={load.overview.recent_hires}
                emptyText="Todavía no hay ingresos para mostrar."
              />
              <RecentPeopleCard
                id="recent-departures"
                title="Salidas recientes"
                linkLabel="Ver todos"
                people={load.overview.recent_departures}
                emptyText="Todavía no hay salidas registradas."
                footnote="Empleados inactivos, ordenados por fecha de fin de contrato."
                muted
              />
            </div>
          )}
          <p className="muted stat-footnote" aria-live="polite">
            Se actualizan automáticamente cada 30 segundos.{' '}
            <Link to="/empleados">Ver directorio de empleados</Link>
          </p>
        </>
      )}
    </section>
  )
}
