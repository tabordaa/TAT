import { Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from './useAuth'

export const CHANGE_PASSWORD_PATH = '/cambiar-contrasena'

// UX guard only. The REAL protection is on the server (get_current_user):
// anyone can bypass frontend code, nobody can bypass the API's 401.
export function ProtectedRoute() {
  const { user, isLoading } = useAuth()
  const { pathname } = useLocation()

  if (isLoading) {
    return <div className="page-loading">Cargando…</div>
  }
  if (user === null) {
    return <Navigate to="/login" replace />
  }
  // HU-1.2: with a temporary password, every route leads to the change screen.
  if (user.must_change_password && pathname !== CHANGE_PASSWORD_PATH) {
    return <Navigate to={CHANGE_PASSWORD_PATH} replace />
  }
  return <Outlet />
}
