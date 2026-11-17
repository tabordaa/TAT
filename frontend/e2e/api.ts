import { expect, request, type APIRequestContext, type Page } from '@playwright/test'
import type { UserRole } from '../src/types/auth'
import type { ContractType, EmployeeCreated, EmployeeCreatePayload } from '../src/types/employee'
import { storageStateFor, type Role } from './accounts'
import { businessDate, randomPassword, randomPerson, type Person } from './data'
import { BASE_URL } from './session'

// Setup through the API, so each spec drives in the browser only the flow it
// verifies. Everything goes through the same /api proxy the browser uses.

/** An API client signed in as one of the seeded roles. Dispose it when done. */
export async function apiAs(role: Role): Promise<APIRequestContext> {
  return request.newContext({ baseURL: BASE_URL, storageState: storageStateFor(role) })
}

interface NewEmployeeOptions {
  accountRole?: UserRole
  contractType?: ContractType
  startDate?: string
  endDate?: string | null
}

export interface CreatedEmployee {
  person: Person
  id: string
  /** Only when an account was requested: shown once by the API. */
  temporaryPassword: string | null
}

/** Registers a realistic employee as the seeded ADMIN (optionally with an account). */
export async function createEmployee(options: NewEmployeeOptions = {}): Promise<CreatedEmployee> {
  const person = randomPerson()
  const payload: EmployeeCreatePayload = {
    first_names: person.firstNames,
    last_names: person.lastNames,
    document_type: 'CC',
    document_number: person.documentNumber,
    email: person.email,
    phone: person.phone,
    position: person.position,
    area: person.area,
    salary: person.salary,
    contract_type: options.contractType ?? 'INDEFINIDO',
    start_date: options.startDate ?? businessDate(-400),
    end_date: options.endDate ?? null,
    ...(options.accountRole !== undefined && { account_role: options.accountRole }),
  }
  const admin = await apiAs('ADMIN')
  try {
    const response = await admin.post('/api/employees', { data: payload })
    expect(response.status(), 'POST /employees').toBe(201)
    const created = (await response.json()) as EmployeeCreated
    return {
      person,
      id: created.id,
      temporaryPassword: created.account?.temporary_password ?? null,
    }
  } finally {
    await admin.dispose()
  }
}

/** Replaces a temporary password with a new random one, as the person would on first sign-in. */
export async function activateAccount(email: string, temporaryPassword: string): Promise<string> {
  const context = await request.newContext({ baseURL: BASE_URL })
  try {
    const login = await context.post('/api/auth/login', {
      data: { email, password: temporaryPassword },
    })
    expect(login.status(), 'login with the temporary password').toBe(200)
    const password = randomPassword()
    const change = await context.post('/api/auth/change-password', {
      data: { current_password: temporaryPassword, new_password: password },
    })
    expect(change.status(), 'change the temporary password').toBe(200)
    return password
  } finally {
    await context.dispose()
  }
}

/** An employee with an active account and a password of their own (no forced change). */
export async function createEmployeeWithAccount(
  role: UserRole = 'EMPLOYEE',
  options: Omit<NewEmployeeOptions, 'accountRole'> = {},
): Promise<CreatedEmployee & { password: string }> {
  const created = await createEmployee({ ...options, accountRole: role })
  if (created.temporaryPassword === null) throw new Error('the API returned no account')
  const password = await activateAccount(created.person.email, created.temporaryPassword)
  return { ...created, password }
}

/** Status of POST /auth/login for these credentials, from a fresh client. */
export async function loginStatus(email: string, password: string): Promise<number> {
  const context = await request.newContext({ baseURL: BASE_URL })
  try {
    const response = await context.post('/api/auth/login', { data: { email, password } })
    return response.status()
  } finally {
    await context.dispose()
  }
}

/** Signs the page's browser context in (the cookie is shared with the page). */
export async function signIn(page: Page, email: string, password: string): Promise<void> {
  const response = await page.request.post('/api/auth/login', { data: { email, password } })
  expect(response.status(), 'sign in').toBe(200)
}

/** Ends the current contract as the seeded ADMIN. */
export async function terminateContract(employeeId: string, endDate = businessDate()): Promise<void> {
  const admin = await apiAs('ADMIN')
  try {
    const response = await admin.post(`/api/employees/${employeeId}/contracts/terminate`, {
      data: { end_date: endDate },
    })
    expect(response.status(), 'terminate the contract').toBe(200)
  } finally {
    await admin.dispose()
  }
}
