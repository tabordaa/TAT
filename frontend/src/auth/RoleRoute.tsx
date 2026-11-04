import { Navigate, Outlet } from 'react-router'
import type { UserRole } from '../types/auth'
import { useAuth } from './useAuth'

// UX guard only, like ProtectedRoute: the API answers 403 whatever the UI shows.
// Goes inside ProtectedRoute, which has already resolved the session.
export function RoleRoute({ allowed }: { allowed: readonly UserRole[] }) {
  const { user } = useAuth()

  if (user === null || !allowed.includes(user.role)) {
    return <Navigate to="/" replace />
  }
  return <Outlet />
}
