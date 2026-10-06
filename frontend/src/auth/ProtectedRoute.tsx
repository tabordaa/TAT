import { Navigate, Outlet } from 'react-router'
import { useAuth } from './useAuth'

// UX guard only. The REAL protection is on the server (get_current_user):
// anyone can bypass frontend code, nobody can bypass the API's 401.
export function ProtectedRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <div className="page-loading">Cargando…</div>
  }
  if (user === null) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}
