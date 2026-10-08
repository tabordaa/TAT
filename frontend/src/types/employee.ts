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
  contractType: ContractType | ''
  startDate: string
  endDate: string
}

export type EmployeeFormErrors = Partial<Record<keyof EmployeeFormValues, string>>

export type EmployeeStatus = 'ACTIVO' | 'INACTIVO'

/** Body of POST /employees (mirrors backend EmployeeCreate, snake_case). */
export interface EmployeeCreatePayload {
  first_names: string
  last_names: string
  document_type: DocumentType
  document_number: string
  email: string | null
  phone: string | null
  position: string
  area: string | null
  contract_type: ContractType
  start_date: string
  end_date: string | null
}

/** Response of POST /employees (mirrors backend EmployeeResponse). */
export interface Employee extends EmployeeCreatePayload {
  id: string
  status: EmployeeStatus
  created_at: string
}
