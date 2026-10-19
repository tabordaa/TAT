import type { UserRole } from './auth'

// HU-2.1 contract (frontend side). The backend schema will mirror it.

export const DOCUMENT_TYPES = {
  CC: 'Cédula de ciudadanía (CC)',
  CE: 'Cédula de extranjería (CE)',
  PA: 'Pasaporte (PA)',
  PPT: 'Permiso por Protección Temporal (PPT)',
} as const
export type DocumentType = keyof typeof DOCUMENT_TYPES

export const CONTRACT_TYPES = {
  INDEFINIDO: 'Término indefinido',
  FIJO: 'Término fijo',
  OBRA_LABOR: 'Obra o labor',
  APRENDIZAJE: 'Aprendizaje',
} as const
export type ContractType = keyof typeof CONTRACT_TYPES

/** Contracts that require an end date. */
export const CONTRACTS_WITH_END_DATE: readonly ContractType[] = ['FIJO', 'OBRA_LABOR', 'APRENDIZAJE']

export interface EmployeeFormValues {
  firstNames: string
  lastNames: string
  documentType: DocumentType | ''
  documentNumber: string
  email: string
  phone: string
  position: string
  area: string
  salary: string
  contractType: ContractType | ''
  startDate: string
  endDate: string
  /** Role of the access account to create together with the employee; '' = no account. */
  accountRole: UserRole | ''
}

export type EmployeeFormErrors = Partial<Record<keyof EmployeeFormValues, string>>

export type EmployeeStatus = 'ACTIVO' | 'INACTIVO'

/** Body of POST /employees (mirrors backend EmployeeCreate, snake_case). */
export interface EmployeeCreatePayload {
  first_names: string
  last_names: string
  document_type: DocumentType
  document_number: string
  email: string
  phone: string | null
  position: string
  area: string
  /** Decimal as string (e.g. "2500000.50"): never a float for money. */
  salary: string
  contract_type: ContractType
  start_date: string
  end_date: string | null
  /** Optional (ADMIN only): also create an access account with this role. */
  account_role?: UserRole
}

/** 409 body of POST /employees: which unique field is already taken. */
export interface EmployeeConflict {
  field: 'document_number' | 'email'
  message: string
}

/** Response of GET /employees/{id} (mirrors backend EmployeeResponse). */
export interface Employee extends Omit<EmployeeCreatePayload, 'account_role'> {
  id: string
  status: EmployeeStatus
  created_at: string
}

/** Access account created together with an employee (HU-1.4). */
export interface AccountCreated {
  email: string
  role: UserRole
  /** Shown ONCE: the server keeps only its hash and cannot show it again. */
  temporary_password: string
  must_change_password: boolean
}

/** Response of POST /employees (mirrors backend EmployeeCreatedResponse). */
export interface EmployeeCreated extends Employee {
  account: AccountCreated | null
}

/** One row of GET /employees (mirrors backend EmployeeListItem; no salary or email). */
export interface EmployeeListItem {
  id: string
  first_names: string
  last_names: string
  document_type: DocumentType
  document_number: string
  position: string
  area: string
  start_date: string
  status: EmployeeStatus
}

/** Response of GET /employees (mirrors backend EmployeeListResponse). */
export interface EmployeeListResponse {
  items: EmployeeListItem[]
  /** Rows matching the filters across ALL pages. */
  total: number
  page: number
  size: number
}

/** Query of GET /employees. An empty status means "all"; an empty q means no search. */
export interface EmployeeListQuery {
  /** Words to find in names or document number. Empty means no search. */
  q: string
  status: EmployeeStatus | ''
  page: number
  size: number
}
