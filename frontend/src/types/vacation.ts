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
