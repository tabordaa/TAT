import { api } from './client'
import type {
  CalendarAbsence,
  VacationBalance,
  VacationInboxItem,
  VacationRequest,
  VacationRequestPayload,
  VacationStatus,
} from '../types/vacation'

/** GET /vacation-requests (ADMIN and HR): the inbox, PENDIENTE unless asked otherwise. */
export async function getVacationInbox(
  status: VacationStatus = 'PENDIENTE',
  signal?: AbortSignal,
): Promise<VacationInboxItem[]> {
  const { data } = await api.get<VacationInboxItem[]>('/vacation-requests', {
    params: { status },
    signal,
  })
  return data
}

/** GET /vacation-calendar?month=YYYY-MM (ADMIN, HR and MANAGER). */
export async function getVacationCalendar(
  month: string,
  signal?: AbortSignal,
): Promise<CalendarAbsence[]> {
  const { data } = await api.get<CalendarAbsence[]>('/vacation-calendar', {
    params: { month },
    signal,
  })
  return data
}

/** POST /vacation-requests/{id}/approve (HU-4.2 CA02). */
export async function approveVacationRequest(id: string): Promise<VacationInboxItem> {
  const { data } = await api.post<VacationInboxItem>(
    `/vacation-requests/${encodeURIComponent(id)}/approve`,
  )
  return data
}

/** POST /vacation-requests/{id}/reject (HU-4.2 CA03): the reason is mandatory. */
export async function rejectVacationRequest(id: string, reason: string): Promise<VacationInboxItem> {
  const { data } = await api.post<VacationInboxItem>(
    `/vacation-requests/${encodeURIComponent(id)}/reject`,
    { reason },
  )
  return data
}

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
