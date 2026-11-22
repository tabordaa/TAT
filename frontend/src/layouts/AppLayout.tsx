import { useEffect, useRef, useState } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router'
import { getMyUnseenDecisions, getPendingCount } from '../api/vacations'
import { onVacationsChanged } from '../utils/vacationEvents'
import { useAuth } from '../auth/useAuth'
import { ROLE_LABELS } from '../types/auth'
import { BrandLogo } from '../components/BrandLogo'
import {
  IconCalendar,
  IconChart,
  IconClose,
  IconGrid,
  IconLogout,
  IconMegaphone,
  IconMenu,
  IconShield,
  IconUser,
  IconUsers,
} from '../components/Icons'

// HU-1.3: "Cerrar sesión" is visible on every protected page (it lives in the layout).
export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const menuButtonRef = useRef<HTMLButtonElement>(null)
  const canReadEmployees = user !== null && user.role !== 'EMPLOYEE'
  const isHrStaff = user?.role === 'ADMIN' || user?.role === 'HR'
  const hasRecord = user?.employee_id != null
  const { pathname } = useLocation()
  // HU-4.7: counters next to the vacation links. They refresh on every page
  // change and when a page reports a change; a failure only hides the badge.
  const [pendingCount, setPendingCount] = useState(0)
  const [unseenCount, setUnseenCount] = useState(0)
  const [refreshCount, setRefreshCount] = useState(0)

  useEffect(() => onVacationsChanged(() => setRefreshCount((count) => count + 1)), [])

  useEffect(() => {
    setIsMenuOpen(false)
  }, [pathname])

  useEffect(() => {
    if (!isMenuOpen) return
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsMenuOpen(false)
        menuButtonRef.current?.focus()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isMenuOpen])

  useEffect(() => {
    const controller = new AbortController()
    if (isHrStaff) {
      getPendingCount(controller.signal)
        .then(setPendingCount)
        .catch(() => undefined)
    }
    if (hasRecord) {
      getMyUnseenDecisions(controller.signal)
        .then((news) => setUnseenCount(news.count))
        .catch(() => undefined)
    }
    return () => controller.abort()
  }, [isHrStaff, hasRecord, pathname, refreshCount])

  async function handleLogout() {
    setIsLoggingOut(true)
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-left">
          <button
            ref={menuButtonRef}
            type="button"
            className="menu-toggle"
            aria-controls="app-sidebar"
            aria-expanded={isMenuOpen}
            aria-label={isMenuOpen ? 'Cerrar menú' : 'Abrir menú'}
            onClick={() => setIsMenuOpen((open) => !open)}
          >
            {isMenuOpen ? <IconClose size={20} /> : <IconMenu size={20} />}
          </button>
          <BrandLogo />
          <span className="app-title">TAT · Tracking and Talent</span>
        </div>

        {user !== null && (
          <div className="app-user">
            <div className="app-user-info">
              <span className="app-user-name">{user.full_name}</span>
              <span className="badge badge-success">{ROLE_LABELS[user.role]}</span>
            </div>
            <span className="avatar" aria-hidden="true">
              <IconUser size={16} />
            </span>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void handleLogout()}
              disabled={isLoggingOut}
            >
              <IconLogout />
              <span className="btn-label">{isLoggingOut ? 'Cerrando…' : 'Cerrar sesión'}</span>
            </button>
          </div>
        )}
      </header>

      <div className="app-body">
        {isMenuOpen && (
          <div
            className="sidebar-backdrop"
            aria-hidden="true"
            onClick={() => setIsMenuOpen(false)}
          />
        )}
        <nav
          id="app-sidebar"
          className={isMenuOpen ? 'sidebar is-open' : 'sidebar'}
          aria-label="Navegación principal"
        >
          {user !== null && (
            <div className="sidebar-user">
              <span className="avatar" aria-hidden="true">
                <IconUser size={16} />
              </span>
              <div className="sidebar-user-info">
                <span className="sidebar-user-name">{user.full_name}</span>
                <span className="badge badge-success">{ROLE_LABELS[user.role]}</span>
              </div>
            </div>
          )}
          <p className="sidebar-title">NAVEGACIÓN PRINCIPAL</p>
          {canReadEmployees && (
            <>
              <NavLink to="/dashboard" className="nav-item">
                <IconGrid /> Panel principal
              </NavLink>
              <NavLink to="/empleados" className="nav-item">
                <IconUsers /> Empleados
              </NavLink>
              <NavLink to="/vacaciones/calendario" className="nav-item">
                <IconCalendar /> Calendario de ausencias
              </NavLink>
            </>
          )}
          {user?.employee_id != null && (
            <>
              <NavLink to="/mi-perfil" className="nav-item">
                <IconUser /> Mi perfil
              </NavLink>
              <NavLink to="/mis-vacaciones" className="nav-item">
                <IconCalendar /> Mis vacaciones
                {unseenCount > 0 && (
                  <span className="badge badge-warning nav-badge">
                    {unseenCount === 1 ? '1 novedad' : `${unseenCount} novedades`}
                  </span>
                )}
              </NavLink>
            </>
          )}
          {isHrStaff && (
            <NavLink to="/vacaciones/solicitudes" className="nav-item">
              <IconCalendar /> Solicitudes de vacaciones
              {pendingCount > 0 && (
                <span className="badge badge-warning nav-badge">
                  {pendingCount === 1 ? '1 pendiente' : `${pendingCount} pendientes`}
                </span>
              )}
            </NavLink>
          )}
          {user?.role === 'ADMIN' && (
            <>
              <NavLink to="/festivos" className="nav-item">
                <IconCalendar /> Festivos
              </NavLink>
              <NavLink to="/auditoria" className="nav-item">
                <IconShield /> Auditoría
              </NavLink>
            </>
          )}
          {canReadEmployees && (
            <>
              <span className="nav-item nav-item-disabled" aria-disabled="true">
                <IconMegaphone /> Novedades{' '}
                <span className="badge badge-muted nav-badge">Próximamente</span>
              </span>
              <span className="nav-item nav-item-disabled" aria-disabled="true">
                <IconChart /> Reportes{' '}
                <span className="badge badge-muted nav-badge">Próximamente</span>
              </span>
            </>
          )}
        </nav>

        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
