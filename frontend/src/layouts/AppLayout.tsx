import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router'
import { useAuth } from '../auth/useAuth'
import { BrandLogo } from '../components/BrandLogo'
import {
  IconChart,
  IconGrid,
  IconLogout,
  IconMegaphone,
  IconUser,
  IconUsers,
} from '../components/Icons'

const ROLE_LABELS = { ADMIN: 'Administrador', HR: 'Recursos Humanos' } as const

// HU-1.3: "Cerrar sesión" is visible on every protected page (it lives in the layout).
export function AppLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  async function handleLogout() {
    setIsLoggingOut(true)
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-left">
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
              {isLoggingOut ? 'Cerrando…' : 'Cerrar sesión'}
            </button>
          </div>
        )}
      </header>

      <div className="app-body">
        <nav className="sidebar" aria-label="Navegación principal">
          <p className="sidebar-title">NAVEGACIÓN PRINCIPAL</p>
          <NavLink to="/dashboard" className="nav-item">
            <IconGrid /> Panel principal
          </NavLink>
          <NavLink to="/empleados" className="nav-item">
            <IconUsers /> Empleados
          </NavLink>
          <span className="nav-item nav-item-disabled" aria-disabled="true">
            <IconMegaphone /> Novedades <span className="badge badge-muted">Próximamente</span>
          </span>
          <span className="nav-item nav-item-disabled" aria-disabled="true">
            <IconChart /> Reportes <span className="badge badge-muted">Próximamente</span>
          </span>
        </nav>

        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
