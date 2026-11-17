import path from 'node:path'
import { fileURLToPath } from 'node:url'

// The four accounts created by backend/scripts/e2e_seed.py (keep both in sync).
export type Role = 'ADMIN' | 'HR' | 'MANAGER' | 'EMPLOYEE'

export interface Account {
  role: Role
  email: string
  fullName: string
  roleLabel: string
}

export const ACCOUNTS: Record<Role, Account> = {
  ADMIN: {
    role: 'ADMIN',
    email: 'laura.restrepo@tat.example.com',
    fullName: 'Laura Restrepo Gómez',
    roleLabel: 'Administrador',
  },
  HR: {
    role: 'HR',
    email: 'andres.cardona@tat.example.com',
    fullName: 'Andrés Felipe Cardona Ríos',
    roleLabel: 'Recursos Humanos',
  },
  MANAGER: {
    role: 'MANAGER',
    email: 'catalina.mejia@tat.example.com',
    fullName: 'Catalina Mejía Duque',
    roleLabel: 'Gerente',
  },
  EMPLOYEE: {
    role: 'EMPLOYEE',
    email: 'juan.ospina@tat.example.com',
    fullName: 'Juan David Ospina Henao',
    roleLabel: 'Empleado',
  },
}

export const ROLES = Object.keys(ACCOUNTS) as Role[]

const authDir = path.join(path.dirname(fileURLToPath(import.meta.url)), '.auth')

/** Where global-setup saves the signed-in browser state of each role. */
export function storageStateFor(role: Role): string {
  return path.join(authDir, `${role.toLowerCase()}.json`)
}

/** The shared seed password. Never printed: it only travels to the login form or API. */
export function e2ePassword(): string {
  const password = process.env.E2E_PASSWORD
  if (password === undefined || password.length < 12) {
    throw new Error('E2E_PASSWORD is missing: set it or create frontend/e2e/.env.e2e')
  }
  return password
}
