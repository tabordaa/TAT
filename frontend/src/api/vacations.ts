import { api } from './client'
import type { VacationBalance, VacationRequest, VacationRequestPayload } from '../types/vacation'

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

/** GET /me/vacation-requests: my requests, latest dates first. */
export async function getMyVacationRequests(signal?: AbortSignal): Promise<VacationRequest[]> {
  const { data } = await api.get<VacationRequest[]>('/me/vacation-requests', { signal })
  return data
}

/** POST /me/vacation-requests (HU-4.1). The server validates everything again. */
export async function createVacationRequest(
  payload: VacationRequestPayload,
): Promise<VacationRequest> {
  const { data } = await api.post<VacationRequest>('/me/vacation-requests', payload)
  return data
}
