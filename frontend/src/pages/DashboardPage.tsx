import { useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router'
import axios from 'axios'
import { getEmployeeStats } from '../api/employees'
import { useAuth } from '../auth/useAuth'
import { IconAlert, IconCheck, IconUser, IconUsers } from '../components/Icons'
import type { EmployeeStats } from '../types/employee'

// Numbers are re-read while the dashboard is open, so they follow the database
// without reloading the page (HU-6.1 CA02).
const REFRESH_INTERVAL_MS = 30_000

const numberFormatter = new Intl.NumberFormat('es-CO')

type Load =
  | { phase: 'loading' }
  | { phase: 'forbidden' }
  | { phase: 'error' }
  | { phase: 'ready'; stats: EmployeeStats }

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
      getEmployeeStats(controller.signal)
        .then((stats) => setLoad({ phase: 'ready', stats }))
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
          <p className="muted stat-footnote" aria-live="polite">
            Se actualizan automáticamente cada 30 segundos.{' '}
            <Link to="/empleados">Ver directorio de empleados</Link>
          </p>
        </>
      )}
    </section>
  )
}
