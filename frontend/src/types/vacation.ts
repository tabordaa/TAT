// Mirrors backend/app/schemas/vacation.py (the API contract).

/** GET /me/vacation-balance and GET /employees/{id}/vacation-balance (HU-4.3). */
export interface VacationBalance {
  days_per_year: number
  /** Start of the contract in force; null when there is none (everything is 0). */
  contract_start: string | null
  /** Decimals as strings, like salaries: e.g. "12.34". */
  accrued_days: string
  used_days: number
  pending_days: number
  available_days: string
  requestable_days: string
}

export type VacationStatus = 'PENDIENTE' | 'APROBADA' | 'RECHAZADA' | 'CANCELADA'

export const VACATION_STATUS_LABELS: Record<VacationStatus, string> = {
  PENDIENTE: 'Pendiente',
  APROBADA: 'Aprobada',
  RECHAZADA: 'Rechazada',
  CANCELADA: 'Cancelada',
}

/** POST /me/vacation-requests: only the dates; the server decides the rest. */
export interface VacationRequestPayload {
  start_date: string
  end_date: string
}

/** A vacation request (HU-4.1). Dates as YYYY-MM-DD, instants as ISO 8601. */
export interface VacationRequest {
  id: string
  start_date: string
  end_date: string
  business_days: number
  status: VacationStatus
  reason: string | null
  created_at: string
  decided_at: string | null
}

/** GET /vacation-calendar (HU-4.4): an approved absence touching the month. */
export interface CalendarAbsence {
  request_id: string
  employee_id: string
  employee_name: string
  start_date: string
  end_date: string
}

/** GET /vacation-requests (HU-4.2): a request in HR's inbox. */
export interface VacationInboxItem extends VacationRequest {
  employee_id: string
  employee_name: string
  /** What the employee has available; the approval is checked against it. */
  available_days: string
}
