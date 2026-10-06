// Mirrors backend/app/schemas/auth.py (the API contract).

export type UserRole = 'ADMIN' | 'HR'

export interface User {
  id: string
  email: string
  full_name: string
  role: UserRole
}

export interface LoginCredentials {
  email: string
  password: string
}
