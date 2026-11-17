import { api } from './client'
import type { VacationBalance } from '../types/vacation'

/** GET /me/vacation-balance: the signed-in person's balance (no id: it comes from the session). */
export async function getMyVacationBalance(signal?: AbortSignal): Promise<VacationBalance> {
  const { data } = await api.get<VacationBalance>('/me/vacation-balance', { signal })
  return data
}

/** GET /employees/{id}/vacation-balance (ADMIN, HR and MANAGER). */
export async function getVacationBalance(
  employeeId: string,
  signal?: AbortSignal,
): Promise<VacationBalance> {
  const { data } = await api.get<VacationBalance>(
    `/employees/${encodeURIComponent(employeeId)}/vacation-balance`,
    { signal },
  )
  return data
}
