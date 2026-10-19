// Mirrors backend/app/schemas/auth.py (the API contract).

export type UserRole = 'ADMIN' | 'MANAGER' | 'HR' | 'EMPLOYEE'

/** UI labels for each role (the API and the database use the English values). */
export const ROLE_LABELS: Record<UserRole, string> = {
  ADMIN: 'Administrador',
  MANAGER: 'Gerente',
  HR: 'Recursos Humanos',
  EMPLOYEE: 'Empleado',
}

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
  employee_id: string | null
  /** True while the account still uses a temporary password (HU 1.2 will force the change). */
  must_change_password: boolean
}

export interface LoginCredentials {
  email: string
  password: string
}
