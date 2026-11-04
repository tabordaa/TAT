import { api } from './client'
import type { Employee } from '../types/employee'

/** GET /me/employee: the record linked to this session. 404 if the account has none. */
export async function getMyEmployee(signal?: AbortSignal): Promise<Employee> {
  const { data } = await api.get<Employee>('/me/employee', { signal })
  return data
}
