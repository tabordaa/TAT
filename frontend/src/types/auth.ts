// Mirrors backend/app/schemas/auth.py (the API contract).

export type UserRole = 'ADMIN' | 'MANAGER' | 'HR' | 'EMPLOYEE'

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
