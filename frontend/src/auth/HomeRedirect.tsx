import { Navigate } from 'react-router'
import { useAuth } from './useAuth'

// HU-2.6 CA01: an employee lands on their own profile, everyone else on the panel.
export function HomeRedirect() {
  const { user } = useAuth()
  return <Navigate to={user?.role === 'EMPLOYEE' ? '/mi-perfil' : '/dashboard'} replace />
}
