import { api } from './client'
import type { ContactPayload, Employee } from '../types/employee'

export const MY_PHOTO_URL = '/api/me/employee/photo'

/** GET /me/employee: the record linked to this session. 404 if the account has none. */
export async function getMyEmployee(signal?: AbortSignal): Promise<Employee> {
  const { data } = await api.get<Employee>('/me/employee', { signal })
  return data
}

/** PATCH /me/employee: contact fields only; the API rejects anything else. */
export async function updateMyContact(payload: ContactPayload): Promise<Employee> {
  const { data } = await api.patch<Employee>('/me/employee', payload)
  return data
}

/** PUT /me/employee/photo. */
export async function uploadMyPhoto(file: File): Promise<Employee> {
  const form = new FormData()
  form.append('photo', file)
  const { data } = await api.put<Employee>('/me/employee/photo', form, {
    // Replaces the client's JSON default; the browser adds the boundary itself.
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}
